import unittest

import numpy as np
import pandas as pd

from ix.core.macro.backtest import run_backtest
from ix.core.macro.engine import (
    compute_allocation,
    compute_regime_probabilities,
    compute_transition_matrix,
    project_probabilities,
)
from ix.core.quant.correlation import correlation_matrix
from ix.core.quant.pca import pca_decomposition
from ix.core.quant.regression import ols_regression, rolling_beta
from ix.core.quant.var import expected_shortfall, historical_var, parametric_var
from ix.core.transforms import Drawdown


class FinancialRobustnessTests(unittest.TestCase):
    def test_ols_regression_drops_constant_factors(self):
        index = pd.date_range("2024-01-01", periods=6, freq="D")
        y = pd.Series([1.0, 1.1, 1.4, 1.6, 1.9, 2.2], index=index)
        factors = pd.DataFrame(
            {
                "trend": [0.5, 0.7, 0.9, 1.2, 1.4, 1.8],
                "constant": [3.0] * 6,
            },
            index=index,
        )

        result = ols_regression(y, factors)

        self.assertIn("trend", result["coefficients"])
        self.assertNotIn("constant", result["coefficients"])
        self.assertEqual(result["dropped_factors"], ["constant"])
        self.assertEqual(result["observations"], 6)

    def test_rolling_beta_avoids_infinite_values_with_zero_variance_benchmark(self):
        index = pd.date_range("2024-01-01", periods=8, freq="D")
        y = pd.Series([100, 102, 101, 104, 103, 105, 108, 109], index=index)
        x = pd.Series([100] * 8, index=index)

        beta = rolling_beta(y, x, window=3)

        self.assertFalse(np.isinf(beta.fillna(0)).any())
        self.assertTrue(beta.dropna().empty)

    def test_var_and_expected_shortfall_flatline_to_zero(self):
        index = pd.date_range("2024-01-01", periods=10, freq="D")
        series = pd.Series([100.0] * 10, index=index)

        hist = historical_var(series, confidence=0.95)
        para = parametric_var(series, confidence=0.95)
        es = expected_shortfall(series, confidence=0.95)

        self.assertEqual(hist["var"], 0.0)
        self.assertEqual(para["var"], 0.0)
        self.assertEqual(es["es"], 0.0)

    def test_correlation_matrix_handles_constant_series(self):
        index = pd.date_range("2024-01-01", periods=6, freq="D")
        df = pd.DataFrame(
            {
                "risk": [100, 101, 103, 102, 104, 105],
                "flat": [50, 50, 50, 50, 50, 50],
            },
            index=index,
        )

        corr = correlation_matrix(df)

        self.assertEqual(corr.shape, (2, 2))
        self.assertTrue(np.isfinite(corr.values).all())
        self.assertEqual(float(corr.loc["flat", "flat"]), 1.0)

    def test_pca_drops_constant_return_columns(self):
        index = pd.date_range("2024-01-01", periods=8, freq="D")
        df = pd.DataFrame(
            {
                "asset_a": [100, 101, 102, 104, 103, 105, 107, 108],
                "asset_b": [50, 49, 51, 53, 54, 55, 57, 58],
                "flat": [10] * 8,
            },
            index=index,
        )

        result = pca_decomposition(df, n_components=2)

        self.assertIn("flat", result["dropped_columns"])
        self.assertEqual(list(result["loadings"].index), ["asset_a", "asset_b"])
        self.assertEqual(result["components"].shape[1], 2)

    def test_regime_probabilities_and_transition_matrix_stay_normalized(self):
        index = pd.date_range("2024-01-05", periods=6, freq="W-FRI")
        growth = pd.Series([10, 11, 12, 13, 14, 15], index=index)
        inflation = pd.Series([-10, -11, -12, -13, -14, -15], index=index)

        probs = compute_regime_probabilities(growth, inflation, temperature=1e-9)
        row_sums = probs.sum(axis=1).round(10)
        transition = compute_transition_matrix(probs.iloc[:1])
        projected = project_probabilities(np.array([1.0, 0.0, 0.0, 0.0]), transition, 5)

        self.assertTrue((row_sums == 1.0).all())
        self.assertTrue(np.allclose(np.diag(transition.values), 1.0))
        self.assertTrue(np.allclose(projected.sum(), 1.0))

    def test_compute_allocation_works_without_regime_probabilities(self):
        index = pd.date_range("2024-01-05", periods=4, freq="W-FRI")
        liq_phase = pd.Series(["Winter", "Spring", "Summer", "Fall"], index=index)
        tactical = pd.Series([-2.0, 0.0, 2.0, 1.0], index=index)

        alloc = compute_allocation(
            pd.DataFrame(),
            liq_phase,
            tactical,
            regime_weight=2.0,
            liquidity_weight=2.0,
            tactical_weight=1.0,
        )

        self.assertEqual(len(alloc), 4)
        self.assertTrue(((alloc >= 0.10) & (alloc <= 0.90)).all())

    def test_backtest_returns_empty_outputs_for_empty_allocation(self):
        px_index = pd.date_range("2024-01-05", periods=5, freq="W-FRI")
        target_px = pd.Series([100, 101, 102, 103, 104], index=px_index)

        equity_df, weights, stats_df = run_backtest(
            pd.Series(dtype=float),
            target_px,
            "Test Asset",
        )

        self.assertTrue(equity_df.empty)
        self.assertTrue(weights.empty)
        self.assertTrue(stats_df.empty)

    def test_drawdown_returns_negative_fraction_from_peak(self):
        index = pd.date_range("2024-01-01", periods=4, freq="D")
        series = pd.Series([100.0, 120.0, 90.0, 110.0], index=index)

        drawdown = Drawdown(series)

        self.assertEqual(drawdown.iloc[0], 0.0)
        self.assertAlmostEqual(drawdown.iloc[2], -0.25)


if __name__ == "__main__":
    unittest.main()
