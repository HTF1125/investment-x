import unittest

from ix.utils.safe_custom_code import (
    SAFE_CUSTOM_CHART_BUILTINS,
    UnsafeCustomChartCodeError,
    validate_custom_chart_code,
)


class SafeCustomCodeTests(unittest.TestCase):
    def test_allows_supported_chart_script(self):
        code = """
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, Tuple
from ix.db.query import Series, MultiSeries, Offset, Rebase, Cycle, StandardScalar, MonthEndOffset

class ChartTheme:
    pass

def build_labels(items):
    labels: Dict[str, int] = {str(i): i for i in items}
    return labels

for idx, label in enumerate(["A", "B"]):
    if idx >= 0:
        continue

fig = go.Figure()
"""
        validate_custom_chart_code(code)

    def test_rejects_forbidden_import(self):
        with self.assertRaisesRegex(
            UnsafeCustomChartCodeError, "Importing os is not allowed"
        ):
            validate_custom_chart_code("import os\nfig = None\n")

    def test_rejects_forbidden_attribute(self):
        with self.assertRaisesRegex(
            UnsafeCustomChartCodeError, "Forbidden attribute: to_csv"
        ):
            validate_custom_chart_code(
                "import pandas as pd\n"
                "df = pd.DataFrame({'x': [1]})\n"
                "df.to_csv('x.csv')\n"
            )

    def test_rejects_attribute_traversal_to_os(self):
        with self.assertRaisesRegex(
            UnsafeCustomChartCodeError, "Forbidden attribute: os"
        ):
            validate_custom_chart_code(
                "import pandas as pd\npd.io.common.os.system('whoami')\n"
            )

    def test_allows_keyword_unpacking_for_safe_chart_calls(self):
        code = """
import plotly.graph_objects as go
grid_params = {"showgrid": True}
fig = go.Figure()
fig.update_xaxes(title="Test", **grid_params)
"""
        validate_custom_chart_code(code)

    def test_safe_import_wrapper_allows_time(self):
        safe_import = SAFE_CUSTOM_CHART_BUILTINS["__import__"]
        module = safe_import("time", {}, {}, (), 0)
        self.assertEqual(getattr(module, "__name__", None), "time")

    def test_safe_import_wrapper_rejects_blocked_module(self):
        safe_import = SAFE_CUSTOM_CHART_BUILTINS["__import__"]
        with self.assertRaisesRegex(
            UnsafeCustomChartCodeError, "Importing os is not allowed"
        ):
            safe_import("os", {}, {}, (), 0)


if __name__ == "__main__":
    unittest.main()
