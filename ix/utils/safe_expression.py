import ast
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ix.core import ContributionToGrowth
from ix.db import query as query_module


MAX_EXPRESSION_LENGTH = 4000

_BLOCKED_ATTRIBUTE_NAMES = {
    "agg",
    "aggregate",
    "apply",
    "eval",
    "exec",
    "map",
    "pipe",
    "query",
    "read_csv",
    "read_excel",
    "read_feather",
    "read_fwf",
    "read_hdf",
    "read_html",
    "read_json",
    "read_orc",
    "read_parquet",
    "read_pickle",
    "read_sql",
    "read_sql_query",
    "read_sql_table",
    "read_table",
    "read_xml",
    "to_clipboard",
    "to_csv",
    "to_excel",
    "to_feather",
    "to_hdf",
    "to_html",
    "to_json",
    "to_latex",
    "to_markdown",
    "to_parquet",
    "to_pickle",
    "to_sql",
    "to_string",
    "to_xml",
}

_ROOT_ATTRIBUTE_ALLOWLIST = {
    "pd": {
        "DataFrame",
        "DateOffset",
        "Index",
        "NaT",
        "NA",
        "Series",
        "Timestamp",
        "Timedelta",
        "concat",
        "date_range",
        "isna",
        "notna",
        "to_datetime",
    },
    "np": {
        "abs",
        "inf",
        "isfinite",
        "isinf",
        "isnan",
        "log",
        "mean",
        "nan",
        "nanmean",
        "nanmedian",
        "nanstd",
        "sqrt",
        "std",
        "where",
    },
}

_ALLOWED_NODE_TYPES = (
    ast.Add,
    ast.And,
    ast.Attribute,
    ast.BinOp,
    ast.BitAnd,
    ast.BitOr,
    ast.BitXor,
    ast.BoolOp,
    ast.Call,
    ast.Compare,
    ast.Constant,
    ast.Dict,
    ast.Div,
    ast.Eq,
    ast.Expression,
    ast.FloorDiv,
    ast.Gt,
    ast.GtE,
    ast.Invert,
    ast.List,
    ast.Load,
    ast.Lt,
    ast.LtE,
    ast.Mod,
    ast.Mult,
    ast.Name,
    ast.Not,
    ast.NotEq,
    ast.Or,
    ast.Pow,
    ast.Slice,
    ast.Sub,
    ast.Subscript,
    ast.Tuple,
    ast.UAdd,
    ast.USub,
    ast.UnaryOp,
    ast.keyword,
)


class UnsafeExpressionError(ValueError):
    """Raised when an expression uses a forbidden syntax or symbol."""


def _build_query_context() -> dict[str, Any]:
    allowed_names = {
        "Series",
        "MultiSeries",
        "Regime1",
        "Resample",
        "PctChange",
        "Diff",
        "MovingAverage",
        "MonthEndOffset",
        "MonthsOffset",
        "Offset",
        "StandardScalar",
        "Clip",
        "Ffill",
        "CycleForecast",
        "Drawdown",
        "Rebase",
        "FinancialConditionsIndex1",
        "FedNetLiquidity",
        "NumOfPmiServicesPositiveMoM",
        "oecd_cli_regime",
        "CustomSeries",
        "NumOfOecdCliMoMPositiveEM",
        "financial_conditions_us",
        "FinancialConditionsKR",
        "NumOfPmiMfgPositiveMoM",
        "USD_Open_Interest",
        "InvestorPositions",
        "InvestorPositionsvsTrend",
        "CalendarYearSeasonality",
        "NumOfOECDLeadingPositiveMoM",
        "M2",
        "LocalIndices",
        "AiCapex",
        "macro_data",
        "NumPositivePercentByRow",
        "GetChart",
    }
    return {
        name: getattr(query_module, name)
        for name in allowed_names
        if hasattr(query_module, name)
    }


SERIES_EXPRESSION_CONTEXT: dict[str, Any] = {
    "Series": query_module.Series,
    "MultiSeries": query_module.MultiSeries,
}

TIMESERIES_EXPRESSION_CONTEXT: dict[str, Any] = {
    **_build_query_context(),
    "pd": pd,
    "np": np,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}

EVALUATION_EXPRESSION_CONTEXT: dict[str, Any] = {
    **TIMESERIES_EXPRESSION_CONTEXT,
    "ContributionToGrowth": ContributionToGrowth,
}


class _SafeExpressionValidator(ast.NodeVisitor):
    def __init__(self, context: Mapping[str, Any]):
        self.allowed_names = set(context.keys())
        self.allowed_callables = {
            name for name, value in context.items() if callable(value)
        }

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeExpressionError(
                f"Unsupported syntax: {type(node).__name__}"
            )
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.allowed_names:
            raise UnsafeExpressionError(f"Unknown name: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_") or node.attr in _BLOCKED_ATTRIBUTE_NAMES:
            raise UnsafeExpressionError(f"Forbidden attribute: {node.attr}")

        root_name = self._get_root_name(node)
        if root_name in _ROOT_ATTRIBUTE_ALLOWLIST:
            if node.attr not in _ROOT_ATTRIBUTE_ALLOWLIST[root_name]:
                raise UnsafeExpressionError(
                    f"Forbidden attribute on {root_name}: {node.attr}"
                )

        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in self.allowed_callables:
                raise UnsafeExpressionError(
                    f"Calling {node.func.id} is not allowed"
                )
        elif isinstance(node.func, ast.Attribute):
            self.visit(node.func)
        else:
            raise UnsafeExpressionError("Unsupported callable target")

        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            if keyword.arg is None:
                raise UnsafeExpressionError("Argument unpacking is not allowed")
            self.visit(keyword.value)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self.visit(node.value)
        self.visit(node.slice)

    def visit_Slice(self, node: ast.Slice) -> None:
        if node.lower is not None:
            self.visit(node.lower)
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.visit(node.step)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, (str, int, float, bool, type(None))):
            return
        raise UnsafeExpressionError(
            f"Unsupported constant type: {type(node.value).__name__}"
        )

    @staticmethod
    def _get_root_name(node: ast.AST) -> str | None:
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            return current.id
        return None


def safe_eval_expression(expression: str, context: Mapping[str, Any]) -> Any:
    expression_clean = (expression or "").strip()
    if not expression_clean:
        raise UnsafeExpressionError("Expression cannot be empty")
    if len(expression_clean) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError(
            f"Expression exceeds {MAX_EXPRESSION_LENGTH} characters"
        )

    try:
        tree = ast.parse(expression_clean, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Invalid expression syntax: {exc.msg}") from exc

    _SafeExpressionValidator(context).visit(tree)
    compiled = compile(tree, "<safe-expression>", "eval")
    return eval(compiled, {"__builtins__": {}}, dict(context))
