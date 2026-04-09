"""Safe expression and code block evaluation for timeseries."""

from __future__ import annotations

import math
from typing import List, Optional

import pandas as pd

from ix.common import get_logger
from ix.common.security.safe_expression import (
    TIMESERIES_EXPRESSION_CONTEXT,
    UnsafeExpressionError,
    safe_eval_expression,
    safe_exec_code,
)
from .formatting import _apply_date_bounds

logger = get_logger(__name__)


def evaluate_expression(
    code: str, start_date: Optional[str], end_date: Optional[str]
) -> List[pd.Series]:
    """Evaluate *code* as a Python expression and return a list of Series.

    Returns an empty list on failure (never raises).
    """
    try:
        logger.info(
            "Code %s not found in database, attempting to evaluate as expression",
            code,
        )
        evaluated_series = safe_eval_expression(code, TIMESERIES_EXPRESSION_CONTEXT)
        series_list: List[pd.Series] = []

        if isinstance(evaluated_series, pd.Series):
            evaluated_series.name = code
            if not evaluated_series.empty:
                evaluated_series = _apply_date_bounds(
                    evaluated_series, start_date, end_date
                )
                series_list.append(evaluated_series)
        elif isinstance(evaluated_series, pd.DataFrame):
            for col in evaluated_series.columns:
                col_series = evaluated_series[col].copy()
                col_series.name = col
                col_series = _apply_date_bounds(col_series, start_date, end_date)
                if not col_series.empty:
                    series_list.append(col_series)
        else:
            logger.warning(
                "Evaluated expression %s did not return a Series or DataFrame",
                code,
            )

        return series_list
    except UnsafeExpressionError as e:
        logger.warning("Rejected custom timeseries expression %s: %s", code, e)
        return []
    except Exception as e:
        logger.warning(
            "Code %s not found in database and failed to evaluate as expression: %s",
            code,
            e,
        )
        return []


def execute_code_block(code: str) -> dict:
    """Execute a multi-line code block and return column-oriented dict.

    The code must assign its output to ``result``.
    Raises UnsafeExpressionError for blocked code, or Exception on failure.
    """
    evaluated = safe_exec_code(code, TIMESERIES_EXPRESSION_CONTEXT)
    if isinstance(evaluated, pd.Series):
        df = evaluated.to_frame()
    else:
        df = evaluated
    df.index.name = "Date"
    df = df.sort_index()
    # Format index -- handle both datetime and non-datetime indices
    idx = df.index
    if hasattr(idx, "strftime"):
        dates = [d.strftime("%Y-%m-%d") for d in idx]
    else:
        try:
            dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in idx]
        except Exception:
            dates = [str(d) for d in idx]
    # Column-oriented JSON (same format as timeseries.custom)
    out: dict = {"Date": dates}
    for col in df.columns:
        vals = df[col].tolist()
        out[str(col)] = [
            None
            if (
                v is None
                or (isinstance(v, float) and (pd.isna(v) or not math.isfinite(v)))
            )
            else v
            for v in vals
        ]
    out["__columns__"] = [str(c) for c in df.columns]
    return out
