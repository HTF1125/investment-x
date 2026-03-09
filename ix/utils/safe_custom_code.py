import ast
import builtins
import importlib
from typing import Any

from ix.utils.blocklists import BLOCKED_PANDAS_ATTRIBUTES, BLOCKED_SYSTEM_ATTRIBUTES


MAX_CUSTOM_CHART_CODE_LENGTH = 50000

_BLOCKED_ATTRIBUTE_NAMES = set(BLOCKED_PANDAS_ATTRIBUTES | BLOCKED_SYSTEM_ATTRIBUTES)

_BLOCKED_NAME_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "type",
    "vars",
}

_BLOCKED_IDENTIFIER_NAMES = {
    "__builtins__",
    "__import__",
    "builtins",
    "compile",
    "eval",
    "exec",
    "globals",
    "importlib",
    "locals",
    "open",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "vars",
}

_ALLOWED_IMPORT_MODULES = {
    "datetime",
    "numpy",
    "pandas",
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
    "plotly.subplots",
    "time",
    "typing",
}

_ALLOWED_QUERY_IMPORT_NAMES = {
    "Clip",
    "Cycle",
    "Diff",
    "Ffill",
    "MonthEndOffset",
    "MovingAverage",
    "MultiSeries",
    "Offset",
    "PctChange",
    "Rebase",
    "Resample",
    "Series",
    "StandardScalar",
}

_ALLOWED_IMPORT_FROM_NAMES = {
    "datetime": {"date", "datetime", "timedelta"},
    "ix.db.query": _ALLOWED_QUERY_IMPORT_NAMES,
    "plotly.subplots": {"make_subplots"},
    "typing": {"Dict", "List", "Optional", "Tuple"},
}

_ALLOWED_NODE_TYPES = (
    ast.Add,
    ast.alias,
    ast.And,
    ast.AnnAssign,
    ast.arg,
    ast.arguments,
    ast.Assign,
    ast.Attribute,
    ast.AugAssign,
    ast.BinOp,
    ast.BitAnd,
    ast.BitOr,
    ast.BitXor,
    ast.BoolOp,
    ast.Break,
    ast.Call,
    ast.ClassDef,
    ast.Compare,
    ast.comprehension,
    ast.Constant,
    ast.Continue,
    ast.Dict,
    ast.DictComp,
    ast.Div,
    ast.Eq,
    ast.ExceptHandler,
    ast.Expr,
    ast.FloorDiv,
    ast.For,
    ast.FormattedValue,
    ast.FunctionDef,
    ast.GeneratorExp,
    ast.Gt,
    ast.GtE,
    ast.If,
    ast.IfExp,
    ast.Import,
    ast.ImportFrom,
    ast.In,
    ast.Invert,
    ast.JoinedStr,
    ast.keyword,
    ast.List,
    ast.ListComp,
    ast.Load,
    ast.Lt,
    ast.LtE,
    ast.Mod,
    ast.Module,
    ast.Mult,
    ast.Name,
    ast.Not,
    ast.NotEq,
    ast.NotIn,
    ast.Or,
    ast.Pass,
    ast.Pow,
    ast.Raise,
    ast.Return,
    ast.Set,
    ast.SetComp,
    ast.Slice,
    ast.Store,
    ast.Sub,
    ast.Subscript,
    ast.Try,
    ast.Tuple,
    ast.UAdd,
    ast.UnaryOp,
    ast.USub,
)


class UnsafeCustomChartCodeError(ValueError):
    """Raised when custom chart code uses forbidden syntax or symbols."""


SAFE_CUSTOM_CHART_BUILTINS = {
    "__build_class__": builtins.__build_class__,
    "__import__": None,
    "Exception": Exception,
    "KeyError": KeyError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "TypeError": TypeError,
    "ValueError": ValueError,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "next": next,
    "object": object,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _safe_import(
    name: str,
    globals_dict: dict[str, Any] | None = None,
    locals_dict: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] | list[str] = (),
    level: int = 0,
):
    del globals_dict, locals_dict

    if level != 0:
        raise UnsafeCustomChartCodeError("Relative imports are not allowed")

    requested = (name or "").strip()
    if not requested:
        raise UnsafeCustomChartCodeError("Import target cannot be empty")

    if fromlist:
        allowed_names = _ALLOWED_IMPORT_FROM_NAMES.get(requested)
        if allowed_names is None:
            raise UnsafeCustomChartCodeError(
                f"Importing from {requested} is not allowed"
            )
        for imported_name in fromlist:
            if imported_name == "*" or imported_name not in allowed_names:
                raise UnsafeCustomChartCodeError(
                    f"Importing {imported_name} from {requested} is not allowed"
                )
        return importlib.import_module(requested)

    if requested not in _ALLOWED_IMPORT_MODULES:
        raise UnsafeCustomChartCodeError(f"Importing {requested} is not allowed")

    module = importlib.import_module(requested)
    root_module = requested.split(".", 1)[0]
    return importlib.import_module(root_module) if "." in requested else module


SAFE_CUSTOM_CHART_BUILTINS["__import__"] = _safe_import


class _SafeCustomChartValidator(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeCustomChartCodeError(
                f"Unsupported syntax: {type(node).__name__}"
            )
        super().generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name not in _ALLOWED_IMPORT_MODULES:
                raise UnsafeCustomChartCodeError(
                    f"Importing {alias.name} is not allowed"
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").strip()
        if node.level != 0:
            raise UnsafeCustomChartCodeError("Relative imports are not allowed")
        allowed_names = _ALLOWED_IMPORT_FROM_NAMES.get(module)
        if allowed_names is None:
            raise UnsafeCustomChartCodeError(
                f"Importing from {module or '<unknown>'} is not allowed"
            )
        for alias in node.names:
            if alias.name == "*" or alias.name not in allowed_names:
                raise UnsafeCustomChartCodeError(
                    f"Importing {alias.name} from {module or '<unknown>'} is not allowed"
                )

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__") or node.id in _BLOCKED_IDENTIFIER_NAMES:
            raise UnsafeCustomChartCodeError(f"Forbidden name: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_") or node.attr in _BLOCKED_ATTRIBUTE_NAMES:
            raise UnsafeCustomChartCodeError(f"Forbidden attribute: {node.attr}")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_NAME_CALLS:
            raise UnsafeCustomChartCodeError(f"Calling {node.func.id} is not allowed")
        self.visit(node.func)
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)


def validate_custom_chart_code(code: str) -> None:
    code_clean = (code or "").strip()
    if not code_clean:
        raise UnsafeCustomChartCodeError("Custom chart code cannot be empty")
    if len(code_clean) > MAX_CUSTOM_CHART_CODE_LENGTH:
        raise UnsafeCustomChartCodeError(
            f"Custom chart code exceeds {MAX_CUSTOM_CHART_CODE_LENGTH} characters"
        )

    try:
        tree = ast.parse(code_clean, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCustomChartCodeError(
            f"Invalid custom chart syntax: {exc.msg}"
        ) from exc

    _SafeCustomChartValidator().visit(tree)
