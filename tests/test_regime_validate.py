"""Tests for ``ix.core.regimes.validate.validate_composition``.

These tests require a populated DB (the regime indicators must load) and so
are skipped automatically when the DB or any required series is unavailable.
"""

from __future__ import annotations

import unittest

from ix.core.regimes.validate import (
    CompositionValidationResult,
    validate_composition,
)


def _try_validate(*args, **kwargs):
    """Run the validator, returning ``None`` if the DB / series is unavailable."""
    try:
        return validate_composition(*args, **kwargs)
    except (ValueError, KeyError, ConnectionError, RuntimeError) as exc:
        # Series load / DB / no-data failures → skip
        msg = str(exc).lower()
        if any(s in msg for s in ("could not load", "empty", "not registered", "connection")):
            return None
        raise


class ValidateCompositionTests(unittest.TestCase):
    """End-to-end checks for the composition walk-forward validator."""

    def test_runs_end_to_end_growth_inflation_spy(self):
        """Validator returns a non-null spread + Cohen's d for the canonical
        2-axis composition (growth × inflation → SPY 3M)."""
        r = _try_validate(
            ["growth", "inflation"],
            "SPY US EQUITY:PX_LAST",
            3,
            train_window=24,
        )
        if r is None:
            self.skipTest("DB / SPY series unavailable")

        self.assertIsInstance(r, CompositionValidationResult)
        self.assertGreater(r.n_observations, 100)
        self.assertEqual(r.n_states, 4)  # 2 growth × 2 inflation
        self.assertIsNotNone(r.spread)
        self.assertIsNotNone(r.cohens_d)
        self.assertIsNotNone(r.welch_p)
        self.assertIsNotNone(r.kl_divergence)
        self.assertIn(r.best_state, [
            "Expansion+Falling", "Expansion+Rising",
            "Contraction+Falling", "Contraction+Rising",
        ])

    def test_exclude_indicators_changes_result(self):
        """Excluding the target's own constituent indicator must change the
        outcome — proves the ``exclude`` plumbing reaches ``Regime.build``."""
        without_exclude = _try_validate(
            ["inflation"],
            "CL1 COMDTY:PX_LAST",
            6,
            train_window=24,
        )
        with_exclude = _try_validate(
            ["inflation"],
            "CL1 COMDTY:PX_LAST",
            6,
            train_window=24,
            exclude_indicators={"i_WTI"},
        )

        if without_exclude is None or with_exclude is None:
            self.skipTest("DB / WTI series unavailable")

        # Either spread or Cohen's d must differ — excluding a constituent
        # indicator changes the composite z, which changes H_Dominant, which
        # changes the per-state aggregation.
        self.assertTrue(
            (without_exclude.spread != with_exclude.spread)
            or (without_exclude.cohens_d != with_exclude.cohens_d),
            "exclude_indicators={'i_WTI'} produced an identical result — "
            "the exclude path is not actually reaching the composite.",
        )

    def test_single_regime_baseline_matches_tier1(self):
        """Regression: validating a single registered regime against its
        registered Tier-1 target must reproduce the published spread within a
        small tolerance.

        ``growth → SPY 3M`` is registered with a Tier-1 spread of ~2.14%
        (3-month period return). The validator reports *annualized* spread,
        so we divide by ``12 / horizon`` to get back to the period spread.

        Tolerance is ±1.0% absolute — the validator applies a 1-month
        publication lag (registered baseline does not), and rolling z-score
        windows can shift slightly across data refreshes.
        """
        r = _try_validate(
            ["growth"],
            "SPY US EQUITY:PX_LAST",
            3,
            train_window=24,
        )
        if r is None:
            self.skipTest("DB / SPY series unavailable")

        self.assertIsNotNone(r.spread)
        # Convert annualized → 3-month period return
        period_spread_pct = (r.spread / (12.0 / 3.0)) * 100.0
        tier1_baseline_pct = 2.14
        tolerance_pct = 1.0
        self.assertLess(
            abs(period_spread_pct - tier1_baseline_pct),
            tolerance_pct,
            f"growth → SPY 3M period spread = {period_spread_pct:.2f}%, "
            f"expected ~{tier1_baseline_pct:.2f}% (±{tolerance_pct:.2f}%). "
            f"Walk-forward implementation may be incorrect.",
        )


if __name__ == "__main__":
    unittest.main()
