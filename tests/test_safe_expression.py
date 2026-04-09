import unittest

from ix.common.security.safe_expression import (
    EVALUATION_EXPRESSION_CONTEXT,
    TIMESERIES_EXPRESSION_CONTEXT,
    UnsafeExpressionError,
    safe_eval_expression,
)


class SafeExpressionTests(unittest.TestCase):
    def test_allows_safe_dataframe_expression(self) -> None:
        result = safe_eval_expression(
            "pd.DataFrame({'A': [1, 2], 'B': [3, 4]})",
            EVALUATION_EXPRESSION_CONTEXT,
        )
        self.assertEqual(list(result.columns), ["A", "B"])

    def test_allows_safe_method_chaining(self) -> None:
        result = safe_eval_expression(
            "pd.Series([1, 2, 4]).pct_change().fillna(0)",
            TIMESERIES_EXPRESSION_CONTEXT,
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(float(result.iloc[0]), 0.0)

    def test_rejects_import_execution(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            safe_eval_expression(
                "__import__('os').system('echo hacked')",
                EVALUATION_EXPRESSION_CONTEXT,
            )

    def test_rejects_dunder_access(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            safe_eval_expression(
                "pd.Series([1]).__class__",
                EVALUATION_EXPRESSION_CONTEXT,
            )

    def test_rejects_file_output_methods(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            safe_eval_expression(
                "pd.DataFrame({'A': [1]}).to_csv('out.csv')",
                EVALUATION_EXPRESSION_CONTEXT,
            )


if __name__ == "__main__":
    unittest.main()
