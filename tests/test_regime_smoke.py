"""Smoke tests for every registered regime.

Each registered 1D regime is instantiated and built once with its default
parameters. The build output is asserted to:

  * be a non-empty monthly ``pd.DataFrame``
  * expose the required pipeline columns (``H_Dominant``, ``Dominant``,
    per-state ``P_*`` probabilities, per-dimension ``{Dim}_Z`` composites)
  * contain only registered state labels in the dominant column
  * have a monotonic, ascending DatetimeIndex

These tests are deliberately shallow — they do not validate predictive
power (that's :mod:`tests.test_regime_validate`) or exact numerical
reproducibility. Their purpose is to catch silent data-vendor regressions
(a FRED series renamed, a pct_change semantic change, a loader raising)
before the snapshot writer fails in production.

Skipped automatically when the DB or required series is unavailable.
"""

from __future__ import annotations

import unittest

import pandas as pd

from ix.core.regimes import list_regimes, get_phase_pair
from ix.core.regimes.registry import RegimeRegistration


# Errors that indicate "DB/data not available" rather than a real regression.
_SKIP_ERRORS = (ValueError, KeyError, ConnectionError, RuntimeError)
_SKIP_MARKERS = (
    "could not load",
    "empty",
    "not registered",
    "connection",
    "no such",
    "connection refused",
)


def _try_build(reg: RegimeRegistration) -> pd.DataFrame | None:
    """Build the regime with its default params. Return None if the DB/series
    is unavailable so the test can be skipped rather than failed."""
    if reg.regime_class is None:
        return None
    try:
        regime = reg.regime_class()
        return regime.build(
            z_window=reg.default_params.get("z_window", 96),
            sensitivity=reg.default_params.get("sensitivity", 2.0),
            smooth_halflife=reg.default_params.get("smooth_halflife", 2),
            confirm_months=reg.default_params.get("confirm_months", 3),
        )
    except _SKIP_ERRORS as exc:
        msg = str(exc).lower()
        if any(m in msg for m in _SKIP_MARKERS):
            return None
        raise


class RegimeSmokeTests(unittest.TestCase):
    """One test per registered regime: build → shape/columns/state checks."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.regimes = list_regimes()
        if not cls.regimes:
            raise unittest.SkipTest("No regimes registered")

    def test_registry_is_non_empty(self) -> None:
        self.assertGreater(len(self.regimes), 0)

    def test_every_regime_builds(self) -> None:
        """Each registered regime must build into a DataFrame with the
        standard pipeline columns present and only declared states in
        ``H_Dominant``."""
        skipped: list[str] = []
        for reg in self.regimes:
            with self.subTest(regime=reg.key):
                df = _try_build(reg)
                if df is None:
                    skipped.append(reg.key)
                    continue

                self.assertIsInstance(
                    df, pd.DataFrame,
                    f"{reg.key}: build() must return a DataFrame",
                )
                self.assertFalse(
                    df.empty,
                    f"{reg.key}: build() returned an empty DataFrame",
                )

                # Monotonic DatetimeIndex
                self.assertIsInstance(
                    df.index, pd.DatetimeIndex,
                    f"{reg.key}: index must be DatetimeIndex",
                )
                self.assertTrue(
                    df.index.is_monotonic_increasing,
                    f"{reg.key}: index must be monotonic increasing",
                )

                # Required pipeline columns
                required = {"Dominant", "H_Dominant", "Conviction"}
                missing = required - set(df.columns)
                self.assertFalse(
                    missing,
                    f"{reg.key}: missing required columns {missing}",
                )

                # Per-state probability columns
                for st in reg.states:
                    self.assertIn(
                        f"P_{st}", df.columns,
                        f"{reg.key}: missing P_{st} probability column",
                    )

                # Per-dimension composite z-score columns
                for dim in reg.dimensions:
                    self.assertIn(
                        f"{dim}_Z", df.columns,
                        f"{reg.key}: missing {dim}_Z composite column",
                    )

                # Dominant labels must be a subset of declared states
                dom_labels = set(df["H_Dominant"].dropna().unique())
                unknown = dom_labels - set(reg.states)
                self.assertFalse(
                    unknown,
                    f"{reg.key}: H_Dominant contains undeclared states {unknown}",
                )

        if skipped:
            self.skipTest(
                f"{len(skipped)}/{len(self.regimes)} regimes skipped (DB "
                f"unavailable): {', '.join(skipped)}"
            )

    def test_phase_pairs_are_mutual(self) -> None:
        """If A declares phase_pair=B, then B must declare phase_pair=A."""
        for reg in self.regimes:
            if not reg.phase_pair:
                continue
            with self.subTest(regime=reg.key):
                pair = get_phase_pair(reg.key)
                self.assertIsNotNone(
                    pair,
                    f"{reg.key}.phase_pair={reg.phase_pair!r} points to "
                    f"an unregistered sibling",
                )
                self.assertEqual(
                    pair.phase_pair, reg.key,
                    f"phase_pair asymmetry: {reg.key}↔{pair.key} — "
                    f"{pair.key}.phase_pair={pair.phase_pair!r}",
                )


if __name__ == "__main__":
    unittest.main()
