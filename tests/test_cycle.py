import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from ix.common.data.statistics import Cycle


class CycleTests(unittest.TestCase):
    def test_cycle_falls_back_when_curve_fit_fails(self):
        index = pd.date_range("2020-01-03", periods=120, freq="W-FRI")
        values = np.sin(np.linspace(0, 6 * np.pi, 120)) * 10 + 50
        series = pd.Series(values, index=index)

        with patch("ix.common.data.statistics.curve_fit", side_effect=RuntimeError("boom")):
            result = Cycle(series)

        self.assertEqual(len(result), len(series))
        self.assertTrue(result.index.equals(series.index))
        self.assertFalse(result.isna().any())


if __name__ == "__main__":
    unittest.main()
