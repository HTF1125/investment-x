import os
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Body, status, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from pydantic import BaseModel, Field, validator

# Custom imports (assuming these exist in your project)
from ix.misc import get_logger
from ix.db import Timeseries, EconomicCalendar
from ix.db.models import Timeseries as TimeseriesModel
from ix.db.query import Series
from ix.misc.date import today
from ix.task import update_economic_calendar


logger = get_logger(__name__)






app = FastAPI()


@app.post("/api/upload_data", status_code=status.HTTP_200_OK)
async def upload_data(payload: List[Dict[str, Any]]):
    """
    - 요청 바디로 JSON 리스트를 받고, 'date', 'ticker', 'field', 'value' 컬럼이 있어야 함.
    - Pandas DataFrame으로 변환 후 pivot하여 각 시계열을 DB에 저장.
    """
    try:
        if not isinstance(payload, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload: expected a list of records.",
            )

        df = pd.DataFrame(payload)
        required_columns = {"date", "code", "value"}
        missing = required_columns - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {missing}",
            )

        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])

        pivoted = (
            df.pivot(index="date", columns="code", values="value")
            .sort_index()
            .dropna(how="all", axis=1)
            .dropna(how="all", axis=0)
        )
        for code in pivoted.columns:
            ts = Timeseries.find_one({"code": code}).run()
            if ts is None:
                ts = Timeseries(code=code).create()
            ts.data = pivoted[code].dropna()
        return {"message": f"Successfully received {len(df)} records."}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process VBA upload")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/timeseries_datas", status_code=status.HTTP_200_OK)
async def get_timeseries():
    """
    - DB에 저장된 TimeSeries 중 특정 필드를 제외하고, 2024년 이후 일별(Daily)로 리샘플링하여 반환.
    - 반환 형식: [{ "Date": "YYYY-MM-DD", "<Ticker>:<Field>": value, ... }, ...]
    """
    try:
        datas: List[pd.Series] = []

        for ts in Timeseries.find().run():
            datas.append(ts.data)

        if not datas:
            # 빈 결과인 경우 빈 리스트 반환
            return []

        combined = pd.concat(datas, axis=1).replace(np.nan, None).sort_index()
        combined.index = pd.to_datetime(combined.index)
        combined = combined.resample("D").last().loc["2024":]
        combined.index.name = "Date"
        combined.index = combined.index.strftime("%Y-%m-%d")
        df = combined.reset_index()
        return df.to_dict("records")

    except Exception as e:
        logger.exception("Failed to retrieve timeseries")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/economic_calendar", status_code=status.HTTP_200_OK)
async def _get_economic_calendar():
    """
    - 매 호출 시마다 update_economic_calendar()를 실행하여 최신 데이터를 DB에 반영.
    - EconomicCalendar.get_dataframe()를 호출해 Pandas DataFrame으로 가져온 뒤 JSON으로 반환.
    """
    try:
        from ix.task import update_economic_calendar

        update_economic_calendar()
        df = EconomicCalendar.get_dataframe()
        return df.to_dict("records")

    except Exception as e:
        logger.exception("Failed to fetch economic calendar")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/0.DataLoader.xlsm", status_code=status.HTTP_200_OK)
async def download_file():
    """
    - 로컬의 'docs/0.DataLoader.xlsm' 파일을 다운로드 응답으로 제공.
    - 파일이 없으면 404 에러 반환.
    """
    file_path = os.path.join("docs", "0.DataLoader.xlsm")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        filename="0.DataLoader.xlsm",
    )


from ix.db.models import Timeseries
from fastapi import Body, HTTPException, status


@app.get(
    "/api/timeseries",
    status_code=status.HTTP_200_OK,
    response_model=list[Timeseries],
)
async def api_get_timeseries():
    """
    - JSON 리스트 형태로 전달된 각 행에 대해 id, code 필수.
    - 선택적으로 name, frequency, asset_class, category, fields 컬럼을 처리.
    - fields 컬럼은 'field|source|source_ticker|source_field' 쌍을 '/'로 연결한 문자열.
    """
    return Timeseries.find().run()


@app.post("/api/timeseries", status_code=status.HTTP_200_OK)
async def post_timeseries(payload: list[Timeseries] = Body(...)):
    try:
        processed_count = 0
        for source in payload:
            print(source)
            if source.id is None:
                db_source = Timeseries(**source.model_dump()).create()
            else:
                db_source = Timeseries.get(source.id).run()

            db_source.set(source.model_dump())
            processed_count += 1

        return {"status": "success", "message": f"{processed_count} tickers processed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected server error during ticker upload")
        raise HTTPException(status_code=500, detail=str(e))


from typing import Optional
import numpy as np
import pandas as pd
from fastapi import status, HTTPException
from typing import Annotated
from ix.db.query import Series
from ix.misc.date import today
import json
from ix.db.query import *

from typing import Dict, List, Optional, Any, Union
from fastapi import Query, HTTPException, status
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


@app.get(
    "/api/series",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, List[Optional[Any]]],
    summary="Query one or more series by code",
)
async def get_series(
    series: List[str] = Query(
        ...,
        description="Specify one or more series codes. You can alias a series by using `alias=CODE`.",
    ),
    start: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    include_dates: bool = Query(
        False,
        description="If true, returns a 'date' column and shifts each series into its own list",
    ),
):
    """
    Improved series endpoint that handles various index types (string, float, datetime).
    """
    frames: List[pd.Series] = []

    # Process each series specification
    for spec in series:
        if "=" in spec:
            alias, code = spec.split("=", 1)
            alias = alias.strip()
            code = code.strip()
        else:
            alias, code = spec.strip(), spec.strip()

        try:
            ser = eval(code)

            if isinstance(ser, pd.DataFrame):
                # Handle DataFrame: add all columns as separate series
                for col_name in ser.columns:
                    col_series = ser[col_name].copy()
                    # Use original column name or create compound name if aliased
                    col_series.name = (
                        f"{alias}_{col_name}" if alias != code else col_name
                    )
                    frames.append(col_series)

            elif isinstance(ser, pd.Series):
                ser = ser.copy()
                ser.name = alias
                frames.append(ser)
            else:
                raise ValueError(
                    f"Expected pandas Series or DataFrame, got {type(ser)}"
                )

        except Exception as e:
            logger.error(f"Error processing series code '{code}': {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid series code '{code}': {str(e)}",
            )

    if not frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid series provided"
        )

    # Combine all series into a single DataFrame
    try:
        df = pd.concat(frames, axis=1).round(2)
    except Exception as e:
        logger.error(f"Error concatenating series: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error combining series: {str(e)}",
        )

    # Handle different index types and convert to datetime if possible
    df = _normalize_index(df)

    # Remove rows where all values are NaN
    df = df.dropna(how="all")

    if df.empty:
        logger.warning("All data was filtered out, returning empty result")
        return JSONResponse(content={})

    # Apply date filtering if start/end dates are provided
    df = _apply_date_filtering(df, start, end)

    if df.empty:
        logger.warning("No data remains after date filtering")
        return JSONResponse(content={})

    # Prepare the response payload
    payload = _prepare_response_payload(df, include_dates)

    return JSONResponse(content=payload)


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the DataFrame index to handle string, float, or datetime indices.
    Attempts to convert to datetime where possible.
    """
    try:
        # If index is already datetime, we're good
        if isinstance(df.index, pd.DatetimeIndex):
            return df

        # Try to convert index to datetime
        if df.index.dtype == "object":  # String index
            # Try different date parsing strategies
            try:
                # First, try standard datetime conversion
                df.index = pd.to_datetime(df.index, errors="raise")
                logger.info("Successfully converted string index to datetime")
                return df
            except:
                try:
                    # Try with different formats
                    df.index = pd.to_datetime(
                        df.index, format="%Y-%m-%d", errors="raise"
                    )
                    logger.info(
                        "Successfully converted string index to datetime with explicit format"
                    )
                    return df
                except:
                    try:
                        # Try infer_datetime_format
                        df.index = pd.to_datetime(
                            df.index, infer_datetime_format=True, errors="raise"
                        )
                        logger.info(
                            "Successfully converted string index to datetime with inferred format"
                        )
                        return df
                    except:
                        logger.warning(
                            "Could not convert string index to datetime, keeping as string"
                        )
                        return df

        elif df.index.dtype in ["int64", "float64"]:  # Numeric index
            # Check if numeric values could be Excel date serial numbers or Unix timestamps
            numeric_values = df.index.values

            # Check for Excel date serial numbers (typically 1 to ~50000 for reasonable date range)
            if np.all((numeric_values >= 1) & (numeric_values <= 100000)):
                try:
                    # Try converting as Excel date serial numbers (days since 1900-01-01)
                    base_date = pd.Timestamp("1900-01-01")
                    df.index = pd.to_datetime(
                        base_date + pd.to_timedelta(numeric_values - 1, unit="D")
                    )
                    logger.info(
                        "Successfully converted numeric index as Excel date serial numbers"
                    )
                    return df
                except:
                    pass

            # Check for Unix timestamps (seconds since epoch)
            if np.all(
                (numeric_values >= 946684800) & (numeric_values <= 4102444800)
            ):  # 2000-2100 range
                try:
                    df.index = pd.to_datetime(numeric_values, unit="s")
                    logger.info(
                        "Successfully converted numeric index as Unix timestamps (seconds)"
                    )
                    return df
                except:
                    pass

            # Check for Unix timestamps in milliseconds
            if np.all(
                (numeric_values >= 946684800000) & (numeric_values <= 4102444800000)
            ):
                try:
                    df.index = pd.to_datetime(numeric_values, unit="ms")
                    logger.info(
                        "Successfully converted numeric index as Unix timestamps (milliseconds)"
                    )
                    return df
                except:
                    pass

            logger.warning(
                "Could not convert numeric index to datetime, keeping as numeric"
            )
            return df

        else:
            logger.info(f"Index type {df.index.dtype} kept as-is")
            return df

    except Exception as e:
        logger.error(f"Error normalizing index: {e}")
        return df


def _apply_date_filtering(
    df: pd.DataFrame, start: Optional[str], end: Optional[str]
) -> pd.DataFrame:
    """
    Apply date filtering to the DataFrame based on start and end parameters.
    """
    try:
        if start or end:
            # Only apply date filtering if we have a datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                logger.warning(
                    "Date filtering requested but index is not datetime type"
                )
                return df

            if start:
                try:
                    start_date = pd.to_datetime(start)
                    df = df.loc[df.index >= start_date]
                    logger.info(f"Applied start date filter: {start}")
                except Exception as e:
                    logger.error(f"Error parsing start date '{start}': {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid start date format '{start}'. Use YYYY-MM-DD format.",
                    )

            if end:
                try:
                    end_date = pd.to_datetime(end)
                    df = df.loc[df.index <= end_date]
                    logger.info(f"Applied end date filter: {end}")
                except Exception as e:
                    logger.error(f"Error parsing end date '{end}': {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid end date format '{end}'. Use YYYY-MM-DD format.",
                    )

        return df

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying date filtering: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying date filters: {str(e)}",
        )


def _prepare_response_payload(
    df: pd.DataFrame, include_dates: bool
) -> Dict[str, List[Optional[Any]]]:
    """
    Prepare the response payload based on the include_dates parameter.
    """
    try:
        # Replace NaN values with None for JSON serialization
        df = df.replace({np.nan: None, pd.NaT: None})

        if include_dates:
            # Convert index to string format for consistent JSON serialization
            if isinstance(df.index, pd.DatetimeIndex):
                df.index = df.index.strftime("%Y-%m-%d")
            else:
                # Convert other index types to string
                df.index = df.index.astype(str)

            # Sort by index and reset to create a 'date' column
            df = df.sort_index().reset_index()

            # Rename the index column to something more descriptive
            index_col_name = (
                "date"
                if isinstance(df.iloc[:, 0].iloc[0], str)
                and "-" in str(df.iloc[:, 0].iloc[0])
                else "index"
            )
            df = df.rename(columns={df.columns[0]: index_col_name})

            # Convert to dictionary with lists
            payload = df.to_dict(orient="list")

        else:
            # Return just the series data without index
            payload = {}
            for col in df.columns:
                # Convert series to list, handling different data types
                series_data = df[col].tolist()
                payload[col] = series_data

        # Ensure all values are JSON serializable
        payload = _ensure_json_serializable(payload)

        return payload

    except Exception as e:
        logger.error(f"Error preparing response payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error preparing response: {str(e)}",
        )


def _ensure_json_serializable(obj: Any) -> Any:
    """
    Recursively ensure all values in the object are JSON serializable.
    """
    if isinstance(obj, dict):
        return {key: _ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.strftime("%Y-%m-%d") if hasattr(obj, "strftime") else str(obj)
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj
# Add any additional FastAPI routes below
@app.get("/ping")
async def ping():
    return {"message": "pong"}


from fastapi.middleware.wsgi import WSGIMiddleware

from .dash.app import create_dash_app


@app.get("/status")
def get_status():
    return {"status": "ok"}


from . import dash

# A bit odd, but the only way I've been able to get prefixing of the Dash app
# to work is by allowing the Dash/Flask app to prefix itself, then mounting
# it to root
app.mount(
    "/dash",
    WSGIMiddleware(dash.app.create_dash_app(requests_pathname_prefix="/dash/").server),
)


app.mount(
    "/macro",
    WSGIMiddleware(
        dash.macro.app.create_dash_app(requests_pathname_prefix="/macro/").server
    ),
)
