"""
Evaluation router for executing function code and returning dataframes.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
from collections import OrderedDict
import json
import math
import pandas as pd
from datetime import datetime
from pydantic import BaseModel

from ix.db.conn import ensure_connection
from ix.db.query import *
from ix.misc import get_logger
from ix.core import ContributionToGrowth

logger = get_logger(__name__)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request schema for evaluation endpoint."""

    code: str
    format: Optional[str] = "json"


@router.post("/data/evaluation")
async def evaluate_code(request: EvaluationRequest):
    """
    POST /api/data/evaluation - Evaluate code expression and return dataframe.

    Request body:
    - code: Code expression that evaluates to a DataFrame or Series
    - format: Response format ('json' or 'csv', default: 'json')

    The code will be evaluated with access to module-level imports.

    Example request:
    {
        "code": "pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})"
    }
    """
    ensure_connection()

    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Code string cannot be empty")

    if request.format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Must be 'json' or 'csv'"
        )

    try:
        code = request.code.strip()

        # Evaluate the code expression directly
        result = eval(code, globals(), {})

        # Convert result to DataFrame if it's a Series
        if isinstance(result, pd.Series):
            df = result.to_frame()
        elif isinstance(result, pd.DataFrame):
            df = result.copy()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Code execution result must be a DataFrame or Series, got {type(result).__name__}",
            )

        # Ensure index is named 'Date' if it's a DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            df.index.name = "Date"
        elif df.index.name is None or df.index.name == "":
            df.index.name = "Date"

        # Handle empty dataframe
        if df.empty:
            if request.format == "csv":
                return Response(
                    content="Date\n",
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": "attachment; filename=evaluation_result.csv"
                    },
                )
            else:
                return Response(
                    content=json.dumps({"Date": []}, ensure_ascii=False),
                    media_type="application/json",
                )

        # Format response
        if request.format == "csv":
            csv_data = df.to_csv()
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=evaluation_result.csv"
                },
            )
        else:
            # Return as column-oriented dict
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

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error evaluating code: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing code: {str(e)}")
