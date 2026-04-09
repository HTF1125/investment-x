import ast
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ix.core import ContributionToGrowth
from ix.common.data import transforms as transforms_module
from ix.db import query as query_module
from ix.core import indicators as custom_module
from ix.common.security.blocklists import BLOCKED_PANDAS_ATTRIBUTES


MAX_EXPRESSION_LENGTH = 16000
MAX_CODE_BLOCK_LENGTH = 32000

_BLOCKED_ATTRIBUTE_NAMES = set(BLOCKED_PANDAS_ATTRIBUTES)

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
    ast.comprehension,
    ast.Constant,
    ast.Dict,
    ast.DictComp,
    ast.Div,
    ast.Eq,
    ast.Expression,
    ast.FloorDiv,
    ast.Gt,
    ast.GtE,
    ast.Invert,
    ast.FormattedValue,
    ast.GeneratorExp,
    ast.IfExp,
    ast.JoinedStr,
    ast.List,
    ast.ListComp,
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
    ast.SetComp,
    ast.Slice,
    ast.Starred,
    ast.Sub,
    ast.Subscript,
    ast.Tuple,
    ast.UAdd,
    ast.USub,
    ast.UnaryOp,
    ast.keyword,
    # exec-mode nodes (multi-statement code blocks)
    ast.Module,
    ast.Assign,
    ast.Expr,
    ast.Store,
)


class UnsafeExpressionError(ValueError):
    """Raised when an expression uses a forbidden syntax or symbol."""


def _build_query_context() -> dict[str, Any]:
    # Core query/transform names (from query_module & transforms_module)
    _core_names = {
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
        "Cycle",
        "CycleForecast",
        "Drawdown",
        "Rebase",
        "NumPositivePercentByRow",
        "SimilarPatterns",
    }

    # Dynamically collect all public names exported by ix.core.indicators.
    # This ensures every indicator function and namespace class is available
    # in the chart expression DSL without manual maintenance.
    _indicator_names = {
        name for name in dir(custom_module)
        if not name.startswith("_")
        and name not in ("pd", "np", "Union")  # skip re-exported stdlib
    }

    allowed_names = _core_names | _indicator_names

    sources = [query_module, transforms_module, custom_module]
    result = {}
    for name in allowed_names:
        for src in sources:
            if hasattr(src, name):
                result[name] = getattr(src, name)
                break
    return result


def _strict_query_series(*args: Any, **kwargs: Any) -> Any:
    kwargs.setdefault("strict", True)
    return query_module.Series(*args, **kwargs)


SERIES_EXPRESSION_CONTEXT: dict[str, Any] = {
    "Series": _strict_query_series,
    "MultiSeries": query_module.MultiSeries,
}

TIMESERIES_EXPRESSION_CONTEXT: dict[str, Any] = {
    **_build_query_context(),
    "Series": _strict_query_series,
    "pd": pd,
    "np": np,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "len": len,
    "int": int,
    "float": float,
    "str": str,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "True": True,
    "False": False,
    "None": None,
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
        # Track names created by assignment so they can be used later
        self._assigned_names: set[str] = set()

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeExpressionError(
                f"Unsupported syntax: {type(node).__name__}"
            )
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # Allow assignment targets — register the name
        if isinstance(node.ctx, ast.Store):
            self._assigned_names.add(node.id)
            return
        # Allow context names and previously assigned names
        if node.id not in self.allowed_names and node.id not in self._assigned_names:
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


def safe_exec_code(code: str, context: Mapping[str, Any]) -> Any:
    """Execute a multi-line code block and return the ``result`` variable.

    The code must assign its output to a variable named ``result``
    (pd.DataFrame or pd.Series).  All statements are validated through
    the same AST safety checker used by single-expression eval.
    """
    code_clean = (code or "").strip()
    if not code_clean:
        raise UnsafeExpressionError("Code block cannot be empty")
    if len(code_clean) > MAX_CODE_BLOCK_LENGTH:
        raise UnsafeExpressionError(
            f"Code block exceeds {MAX_CODE_BLOCK_LENGTH} characters"
        )

    try:
        tree = ast.parse(code_clean, mode="exec")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Invalid syntax: {exc.msg}") from exc

    # Pre-collect all assignment/comprehension target names so forward references work
    validator = _SafeExpressionValidator(context)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    validator._assigned_names.add(target.id)
        elif isinstance(node, ast.comprehension):
            if isinstance(node.target, ast.Name):
                validator._assigned_names.add(node.target.id)
    validator.visit(tree)

    compiled = compile(tree, "<safe-code-block>", "exec")
    # Context must be in globals so comprehension scopes can see it
    global_ns: dict[str, Any] = {"__builtins__": {}, **context}
    exec(compiled, global_ns)  # noqa: S102

    result = global_ns.get("result")
    if result is None:
        raise UnsafeExpressionError(
            'Code block must assign output to a variable named "result"'
        )
    if not isinstance(result, (pd.Series, pd.DataFrame)):
        raise UnsafeExpressionError(
            f'"result" must be a DataFrame or Series, got {type(result).__name__}'
        )
    return result
