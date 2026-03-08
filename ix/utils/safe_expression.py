import ast
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ix.core import ContributionToGrowth
from ix.core import transforms as transforms_module
from ix.db import query as query_module
from ix.db import custom as custom_module


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
        "EarningsIndicators",
        "YieldCurve",
        "RealRates",
        "CreditSpreads",
        "RiskAppetite",
        "CitiSurprise",
        "CFTCPositioning",
        "PutCallRatio",
        "ISMIndicators",
        "EarningsGrowth_NTMA",
        "regional_eps_momentum",
        "sector_eps_momentum",
        "regional_eps_breadth",
        "sector_eps_breadth",
        "spx_revision_ratio",
        "spx_revision_breadth",
        "fci_us",
        "fci_kr",
        "fci_stress",
        "fed_net_liquidity",
        "investor_positions_net",
        "investor_positions_vs_trend",
        "usd_open_interest",
        "local_indices_performance",
        "ai_capex_ntma",
        "ai_capex_ltma",
        "ai_capex_q",
        "ai_capex_qoq",
        "ai_capex_total_qoq",
        "ai_capex_total_yoy",
        "us_2s10s",
        "us_3m10y",
        "us_2s30s",
        "kr_2s10s",
        "us_10y_real",
        "us_10y_breakeven",
        "hy_spread",
        "ig_spread",
        "bbb_spread",
        "hy_ig_ratio",
        "spread_zscore",
        "risk_appetite",
        "cesi_data",
        "cesi_breadth",
        "cesi_momentum",
        "cftc_net",
        "cftc_zscore",
        "cftc_extreme_count",
        "put_call_raw",
        "put_call_smoothed",
        "put_call_zscore",
        "ism_manufacturing_data",
        "ism_services_data",
        "ism_new_orders",
        "ism_manufacturing_breadth",
        "ism_services_breadth",
        "ism_new_orders_minus_inventories",
        "ism_new_orders_minus_customers_inventories",
        "ism_manufacturing_momentum_breadth",
        "korea_oecd_cli",
        "korea_pmi_manufacturing",
        "korea_exports_yoy",
        "korea_semi_exports_yoy",
        "korea_consumer_confidence",
        "korea_usdkrw",
        "korea_bond_10y",
        "dollar_index",
        "copper_gold_ratio",
        "em_vs_dm",
        "china_sse",
        "nikkei",
        "vix",
        "commodities_crb",
        "pmi_manufacturing_diffusion",
        "pmi_services_diffusion",
        "pmi_manufacturing_regime",
        "pmi_services_regime",
        "oecd_cli_diffusion_world",
        "oecd_cli_diffusion_developed",
        "oecd_cli_diffusion_emerging",
        "calendar_year_seasonality",
        "calendar_year_seasonality_rebased",
        "m2_us",
        "m2_eu",
        "m2_uk",
        "m2_cn",
        "m2_jp",
        "m2_kr",
        "m2_ch",
        "m2_ca",
        "m2_world",
        "m2_world_total",
        "m2_world_total_yoy",
        "m2_world_contribution",
        "spx_earnings_yield",
        "spx_erp_nominal",
        "spx_erp_real",
        "erp_zscore",
        "erp_momentum",
        "nasdaq_spx_relative_valuation",
        "EquityValuation",
        "rate_cut_expectations",
        "rate_expectations_momentum",
        "rate_expectations_zscore",
        "term_premium_proxy",
        "policy_rate_level",
        "MonetaryPolicy",
        "asian_exports_yoy",
        "asian_exports_diffusion",
        "asian_exports_momentum",
        "korea_semi_share",
        "global_trade_composite",
        "GlobalTrade",
        "inflation_momentum",
        "inflation_surprise",
        "breakeven_momentum",
        "oil_leading_cpi",
        "commodity_inflation_pressure",
        "InflationIndicators",
        "equity_bond_correlation",
        "risk_on_off_breadth",
        "small_large_cap_ratio",
        "cyclical_defensive_ratio",
        "credit_equity_divergence",
        "vix_realized_vol_spread",
        "IntermarketSignals",
        "us_sector_relative_strength",
        "us_cyclical_defensive_ratio",
        "us_sector_breadth",
        "us_sector_dispersion",
        "kr_sector_relative_strength",
        "kr_cyclical_defensive_ratio",
        "kr_sector_breadth",
        "kr_sector_dispersion",
        "kr_tech_vs_us_tech",
        "kr_financials_vs_us_financials",
        "kr_export_vs_domestic",
        "USSectorRotation",
        "KRSectorRotation",
    }
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
