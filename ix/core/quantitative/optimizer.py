"""Portfolio optimization: mean-variance, risk parity, efficient frontier.

Uses scipy.optimize for all numerical solving — no cvxpy dependency required.
Accepts numpy arrays or pandas objects throughout.
"""

from __future__ import annotations

import warnings
from functools import partial
from typing import Callable, Optional, Union

import numpy as np
import pandas as pd
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Helper functions (standalone, no class needed)
# ---------------------------------------------------------------------------

def portfolio_return(weights: np.ndarray, mu: np.ndarray) -> float:
    """Expected portfolio return: w' * mu."""
    return float(np.dot(weights, mu))


def portfolio_variance(weights: np.ndarray, cov: np.ndarray) -> float:
    """Portfolio variance: w' * Sigma * w."""
    return float(np.dot(weights, cov @ weights))


def portfolio_volatility(weights: np.ndarray, cov: np.ndarray) -> float:
    """Portfolio standard deviation."""
    return float(np.sqrt(max(portfolio_variance(weights, cov), 0.0)))


def portfolio_sharpe(
    weights: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float = 0.0,
) -> float:
    """Sharpe ratio: (ret - rf) / vol."""
    vol = portfolio_volatility(weights, cov)
    if vol < 1e-12:
        return 0.0
    return float((portfolio_return(weights, mu) - rf) / vol)


def risk_contribution(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Marginal risk contribution per asset.

    RC_i = w_i * (Sigma @ w)_i / vol(w).
    """
    vol = portfolio_volatility(weights, cov)
    if vol < 1e-12:
        return np.zeros_like(weights)
    return np.asarray(weights * (cov @ weights) / vol)


def inverse_variance_weights(cov: np.ndarray) -> np.ndarray:
    """1/variance weighting, rescaled to sum to 1."""
    variances = np.diag(cov)
    variances = np.where(variances > 0, variances, 1e-12)
    inv = 1.0 / variances
    return np.asarray(inv / inv.sum())


def tracking_error(
    weights: np.ndarray,
    benchmark_weights: np.ndarray,
    cov: np.ndarray,
) -> float:
    """Ex-ante tracking error: vol of the active-weight portfolio."""
    active = np.asarray(weights) - np.asarray(benchmark_weights)
    return float(np.sqrt(max(float(active @ cov @ active), 0.0)))


# ---------------------------------------------------------------------------
# Optimizer class
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """Constrained portfolio optimizer backed by scipy.optimize (SLSQP).

    Parameters
    ----------
    mu : array-like of expected returns (n,).
    cov : array-like covariance matrix (n, n).
    rf : risk-free rate (scalar, same frequency as mu).

    Examples
    --------
    >>> opt = PortfolioOptimizer(mu, cov)
    >>> opt.add_constraint("weight_bounds", lower=0.0, upper=0.3)
    >>> result = opt.max_sharpe()
    >>> result["weights"]
    """

    def __init__(
        self,
        mu: Union[np.ndarray, pd.Series],
        cov: Union[np.ndarray, pd.DataFrame],
        rf: float = 0.0,
    ) -> None:
        # Preserve index labels if pandas objects are passed
        if isinstance(mu, pd.Series):
            self._labels = list(mu.index)
            mu = mu.values.astype(float)
        elif isinstance(cov, pd.DataFrame):
            self._labels = list(cov.columns)
        else:
            self._labels = None

        self._mu = np.asarray(mu, dtype=float)
        self._cov = np.asarray(cov, dtype=float)
        self._rf = float(rf)
        self._n = len(self._mu)

        if self._cov.shape != (self._n, self._n):
            raise ValueError(
                f"Shape mismatch: mu has {self._n} assets but cov is {self._cov.shape}."
            )

        # Default constraints: weights sum to 1, each in [0, 1]
        self._bounds: list[tuple[float, float]] = [(0.0, 1.0)] * self._n
        self._constraints: list[dict] = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

    # ---- constraint API ---------------------------------------------------

    def add_constraint(self, kind: str, **kwargs) -> "PortfolioOptimizer":
        """Add a constraint.  Returns *self* for chaining.

        Supported *kind* values
        -----------------------
        weight_bounds : per-asset bounds.
            lower (float) = 0.0, upper (float) = 1.0
        total_weight : change the fully-invested constraint.
            value (float)
        target_return : equality constraint on expected return.
            value (float)
        min_return : inequality >= value.
            value (float)
        target_risk : equality constraint on portfolio volatility.
            value (float)
        max_risk : inequality <= value.
            value (float)
        tracking_error : max ex-ante TE vs. benchmark.
            benchmark_weights (array-like), value (float)
        max_active_weight : sum(|w - w_bm|) <= value.
            benchmark_weights (array-like), value (float)
        """
        kind = kind.lower().replace("-", "_")

        if kind == "weight_bounds":
            lo = kwargs.get("lower", 0.0)
            hi = kwargs.get("upper", 1.0)
            self._bounds = [(lo, hi)] * self._n

        elif kind == "total_weight":
            val = kwargs["value"]
            # Replace existing sum-to-one constraint
            self._constraints = [
                c for c in self._constraints
                if not self._is_total_weight_constraint(c)
            ]
            self._constraints.append(
                {"type": "eq", "fun": lambda w, v=val: np.sum(w) - v}
            )

        elif kind == "target_return":
            val = kwargs["value"]
            mu = self._mu.copy()
            self._constraints.append(
                {"type": "eq", "fun": lambda w, v=val, m=mu: np.dot(w, m) - v}
            )

        elif kind == "min_return":
            val = kwargs["value"]
            mu = self._mu.copy()
            self._constraints.append(
                {"type": "ineq", "fun": lambda w, v=val, m=mu: np.dot(w, m) - v}
            )

        elif kind == "target_risk":
            val = kwargs["value"]
            c = self._cov.copy()
            self._constraints.append(
                {"type": "eq", "fun": lambda w, v=val, cv=c: portfolio_volatility(w, cv) - v}
            )

        elif kind == "max_risk":
            val = kwargs["value"]
            c = self._cov.copy()
            self._constraints.append(
                {"type": "ineq", "fun": lambda w, v=val, cv=c: v - portfolio_volatility(w, cv)}
            )

        elif kind == "tracking_error":
            bm = np.asarray(kwargs["benchmark_weights"], dtype=float)
            val = kwargs["value"]
            c = self._cov.copy()
            self._constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w, v=val, b=bm, cv=c: v - tracking_error(w, b, cv),
                }
            )

        elif kind == "max_active_weight":
            bm = np.asarray(kwargs["benchmark_weights"], dtype=float)
            val = kwargs["value"]
            self._constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w, v=val, b=bm: v - np.sum(np.abs(w - b)),
                }
            )

        else:
            raise ValueError(f"Unknown constraint kind: '{kind}'")

        return self

    # ---- optimisation methods ---------------------------------------------

    def min_variance(self) -> dict:
        """Minimum variance portfolio."""
        cov = self._cov
        return self._solve(lambda w: portfolio_variance(w, cov))

    def max_sharpe(self) -> dict:
        """Maximum Sharpe ratio portfolio (minimize negative Sharpe)."""
        mu, cov, rf = self._mu, self._cov, self._rf

        def neg_sharpe(w):
            vol = portfolio_volatility(w, cov)
            if vol < 1e-12:
                return 1e6
            return -(np.dot(w, mu) - rf) / vol

        return self._solve(neg_sharpe)

    def max_return(self, target_risk: float) -> dict:
        """Maximise return subject to a volatility ceiling."""
        mu, cov = self._mu, self._cov
        extra = [
            {"type": "ineq", "fun": lambda w: target_risk - portfolio_volatility(w, cov)}
        ]
        return self._solve(lambda w: -np.dot(w, mu), extra_constraints=extra)

    def risk_parity(self, budgets: Optional[np.ndarray] = None) -> dict:
        """Equal (or custom) risk contribution portfolio.

        Parameters
        ----------
        budgets : target risk budget per asset.  Defaults to 1/n each.
        """
        if budgets is None:
            budgets = np.ones(self._n) / self._n
        budgets = np.asarray(budgets, dtype=float)
        cov = self._cov

        def objective(w):
            vol = portfolio_volatility(w, cov)
            if vol < 1e-12:
                return 1e6
            rc = w * (cov @ w) / vol
            target = budgets * vol
            return float(np.sum((rc - target) ** 2))

        return self._solve(objective)

    def efficient_frontier(self, n_points: int = 50) -> list[dict]:
        """Generate *n_points* portfolios along the efficient frontier.

        Returns a list of result dicts sorted by ascending risk.
        """
        mu, cov = self._mu, self._cov

        # Anchor: minimum-variance portfolio
        mv = self.min_variance()
        min_ret = mv["return"]

        # Find maximum achievable return (highest single-asset return within bounds)
        max_ret = float(np.max(mu))
        if max_ret <= min_ret:
            max_ret = min_ret + 1e-4

        targets = np.linspace(min_ret, max_ret, n_points)
        frontier: list[dict] = []

        for t in targets:
            extra = [
                {"type": "eq", "fun": lambda w, v=t, m=mu: np.dot(w, m) - v},
            ]
            result = self._solve(
                lambda w: portfolio_variance(w, cov),
                extra_constraints=extra,
                warn_on_failure=False,
            )
            if result is not None:
                frontier.append(result)

        return frontier

    def solve(self, objective_fn: Callable) -> dict:
        """Generic solver: minimise a custom objective function over weights."""
        return self._solve(objective_fn)

    # ---- internal ---------------------------------------------------------

    def _solve(
        self,
        objective: Callable,
        extra_constraints: Optional[list[dict]] = None,
        warn_on_failure: bool = True,
    ) -> Optional[dict]:
        constraints = list(self._constraints)
        if extra_constraints:
            constraints.extend(extra_constraints)

        x0 = np.ones(self._n) / self._n
        result = minimize(
            fun=objective,
            x0=x0,
            method="SLSQP",
            bounds=self._bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        if not result.success:
            if warn_on_failure:
                warnings.warn(f"Optimisation did not converge: {result.message}")
            return None

        w = result.x
        mu, cov, rf = self._mu, self._cov, self._rf

        ret = portfolio_return(w, mu)
        vol = portfolio_volatility(w, cov)
        sharpe = (ret - rf) / vol if vol > 1e-12 else 0.0
        rc = risk_contribution(w, cov)

        weights_out: Union[pd.Series, np.ndarray]
        rc_out: Union[pd.Series, np.ndarray]
        if self._labels is not None:
            weights_out = pd.Series(w, index=self._labels, name="weights")
            rc_out = pd.Series(rc, index=self._labels, name="risk_contribution")
        else:
            weights_out = w
            rc_out = rc

        return {
            "weights": weights_out,
            "return": round(ret, 6),
            "risk": round(vol, 6),
            "sharpe": round(sharpe, 4),
            "risk_contribution": rc_out,
        }

    @staticmethod
    def _is_total_weight_constraint(c: dict) -> bool:
        """Heuristic: detect the default sum-to-one eq constraint we set."""
        if c.get("type") != "eq":
            return False
        try:
            test = c["fun"](np.ones(2) / 2)
            return abs(test) < 1e-8
        except Exception:
            return False
