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
from ix.db.query import Series, D_MultiSeries
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request schema for evaluation endpoint."""

    code: str
    format: Optional[str] = "json"


@router.post("/data/evaluation")
async def evaluate_code(request: EvaluationRequest):
    """
    POST /api/data/evaluation - Evaluate function code and return dataframe.

    Request body:
    - code: Long string of function code to evaluate (must return a DataFrame)
    - format: Response format ('json' or 'csv', default: 'json')

    The code will be executed with access to module-level imports.

    Example request:
    {
        "code": "import pandas as pd\\ndf = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})\\nreturn df"
    }
    """
    ensure_connection()

    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Code string cannot be empty")

    if request.format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Must be 'json' or 'csv'"
        )

    eval_locals = {}

    try:
        code = request.code.strip()

        # Check if code is a function definition
        is_function_def = code.strip().startswith("def ") or "\ndef " in code

        # If code contains 'return' but is not a function definition, wrap it in a function
        has_return = "return" in code
        if has_return and not is_function_def:
            # Wrap in a function and call it
            lines = code.split("\n")
            indented_lines = ["    " + line if line.strip() else line for line in lines]
            wrapped_code = "\n".join(
                [
                    "def _evaluate():",
                ]
                + indented_lines
                + ["", "result = _evaluate()"]
            )
            exec(wrapped_code, globals(), eval_locals)
        else:
            # Execute the code directly
            exec(code, globals(), eval_locals)

        # Try to get the result from locals
        result = None

        # Priority order for finding result
        result_vars = ["result", "df", "dataframe", "data"]
        for var in result_vars:
            if var in eval_locals:
                result = eval_locals[var]
                break

        # If code defines a function, try to call it (look for the first function defined)
        if result is None and is_function_def:
            # Find all function names in the code
            import re

            func_matches = re.findall(r"def\s+(\w+)\s*\(", code)
            if func_matches:
                func_name = func_matches[0]  # Get the first function
                if func_name in eval_locals:
                    func = eval_locals[func_name]
                    if callable(func):
                        try:
                            # Try calling with no arguments first
                            result = func()
                        except TypeError as e:
                            # Function might need arguments
                            error_msg = str(e)
                            if (
                                "required" in error_msg.lower()
                                or "missing" in error_msg.lower()
                            ):
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Function '{func_name}' requires arguments. Please call it in your code or provide a function that takes no arguments.",
                                )
                            raise

        # If still no result, try evaluating the last line as an expression
        if result is None:
            lines = [line.strip() for line in code.split("\n") if line.strip()]
            if lines:
                last_line = lines[-1]
                # Skip if last line is a statement (not an expression)
                statement_keywords = [
                    "return",
                    "def",
                    "class",
                    "if",
                    "for",
                    "while",
                    "import",
                    "from",
                    "#",
                    "print",
                    "pass",
                    "break",
                    "continue",
                ]
                if last_line and not any(
                    last_line.startswith(kw) for kw in statement_keywords
                ):
                    try:
                        result = eval(last_line, globals(), eval_locals)
                    except:
                        pass

        # If still no result, raise an error
        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Code execution did not produce a result. Please ensure your code:\n"
                "1. Returns a DataFrame (e.g., 'return df')\n"
                "2. Assigns result to 'df', 'result', 'dataframe', or 'data'\n"
                "3. Ends with an expression that evaluates to a DataFrame\n"
                "4. If defining a function, call it or ensure it returns a DataFrame",
            )

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
