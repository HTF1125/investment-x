"""
Evaluation router for executing function code and returning dataframes.
"""

import asyncio
import json
import math
import re
from collections import OrderedDict
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger
from ix.common.security.safe_expression import (
    EVALUATION_EXPRESSION_CONTEXT,
    UnsafeExpressionError,
    safe_eval_expression,
    safe_exec_code,
)
from ix.db.conn import ensure_connection
from ix.db.models.user import User

logger = get_logger(__name__)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request schema for evaluation endpoint."""

    code: str
    format: Optional[str] = "json"


def _parse_evaluation_body(raw: bytes) -> EvaluationRequest:
    """Parse request body leniently — fix raw newlines/tabs in JSON strings
    that VBA's MSXML2.XMLHTTP sends when cell values contain Alt+Enter."""
    text = raw.decode("utf-8", errors="replace")
    # Escape unescaped control characters inside JSON string values
    text = re.sub(r'(?<!\\)\r\n', r'\\n', text)
    text = re.sub(r'(?<!\\)\n', r'\\n', text)
    text = re.sub(r'(?<!\\)\r', r'\\n', text)
    text = re.sub(r'(?<!\\)\t', r'\\t', text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e.msg}")
    return EvaluationRequest(**data)


def _run_evaluation(code: str, fmt: str) -> Response:
    """Blocking evaluation — runs in a thread."""
    ensure_connection()

    # Determine if code is a single expression or a multi-statement block.
    # Multi-line expressions (e.g. MultiSeries with newlines from Excel
    # Alt+Enter) are still expressions — only use exec mode when there
    # are actual statements (assignments like "result = ...").
    has_statements = code.startswith("result") or "\n" in code and "=" in code.split("\n")[0]
    try:
        import ast
        ast.parse(code, mode="eval")
        is_expression = True
    except SyntaxError:
        is_expression = False

    if is_expression:
        result = safe_eval_expression(code, EVALUATION_EXPRESSION_CONTEXT)
    else:
        result = safe_exec_code(code, EVALUATION_EXPRESSION_CONTEXT)

    if isinstance(result, pd.Series):
        df = result.to_frame()
    elif isinstance(result, pd.DataFrame):
        df = result.copy()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Code execution result must be a DataFrame or Series, got {type(result).__name__}",
        )

    if isinstance(df.index, pd.DatetimeIndex):
        df.index.name = "Date"
    elif df.index.name is None or df.index.name == "":
        df.index.name = "Date"

    if df.empty:
        if fmt == "csv":
            return Response(
                content="Date\n",
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=evaluation_result.csv"},
            )
        return Response(
            content=json.dumps({"Date": []}, ensure_ascii=False),
            media_type="application/json",
        )

    if fmt == "csv":
        return Response(
            content=df.to_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=evaluation_result.csv"},
        )

    df_indexed = df.reset_index()
    column_dict = OrderedDict()
    for col in df_indexed.columns:
        values = df_indexed[col].tolist()
        cleaned_values = []
        for v in values:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                cleaned_values.append(None)
            elif isinstance(v, (pd.Timestamp, datetime)):
                cleaned_values.append(v.isoformat())
            else:
                cleaned_values.append(v)
        column_dict[col] = cleaned_values

    return Response(
        content=json.dumps(column_dict, ensure_ascii=False),
        media_type="application/json",
    )


@router.post("/data/evaluation")
@_limiter.limit("30/minute")
async def evaluate_code(
    request: Request,
    _current_user: User = Depends(get_current_user),
):
    """
    POST /api/data/evaluation - Evaluate code expression and return dataframe.

    Request body:
    - code: Code expression that evaluates to a DataFrame or Series
    - format: Response format ('json' or 'csv', default: 'json')

    The expression is evaluated in a restricted analytics context.

    Example request:
    {
        "code": "MultiSeries(A=Series('SPX Index:PX_LAST'), B=Series('XAU Curncy:PX_LAST'))"
    }
    """
    body = _parse_evaluation_body(await request.body())

    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code string cannot be empty")
    if body.format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be 'json' or 'csv'")

    try:
        return await asyncio.to_thread(_run_evaluation, code, body.format)
    except UnsafeExpressionError as e:
        logger.warning("Rejected evaluation expression: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error evaluating code: %s", e)
        raise HTTPException(status_code=500, detail="Error executing code")
