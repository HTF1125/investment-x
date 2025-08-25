from fastapi import FastAPI, HTTPException, Query, Body, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
import asyncio
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import numpy as np
import pandas as pd
from ix.misc import get_logger
from ix.db import Timeseries, EconomicCalendar
from ix.task import daily

logger = get_logger(__name__)

# NOTE: Do not start/stop the scheduler at import time.
# Create it at module level (optional), but manage its lifecycle in lifespan.
scheduler = AsyncIOScheduler()


async def run_daily_task():
    """Wrapper to run the daily task asynchronously."""
    try:
        logger.info("Running scheduled daily task...")
        # Offload blocking CPU/IO-bound work to a thread
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, daily)
        logger.info("Daily task completed successfully")
    except Exception:
        logger.exception("Failed to run daily task")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ix API starting up...")

    # Ensure no duplicate job ids if app reloads
    scheduler.add_job(
        run_daily_task,
        trigger=IntervalTrigger(hours=1),
        id="daily_task_hourly",
        name="Run daily task every hour",
        replace_existing=True,
    )

    # Start scheduler under the current running loop
    scheduler.start()
    logger.info("Scheduler started - daily task will run every hour")

    # Optionally trigger once on startup:
    # await run_daily_task()

    try:
        yield
    finally:
        # Shutdown
        logger.info("ix API shutting down...")
        # Stop scheduler while the event loop is still alive
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")


app = FastAPI(
    title="ix API",
    description="API for ix timeseries and economic calendar services.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/economic_calendar", response_model=List[EconomicCalendar])
async def get_economic_calendar():
    """
    Fetch and return economic calendar data.
    """
    try:
        from ix.task import update_economic_calendar

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, update_economic_calendar)
        return EconomicCalendar.find().run()
    except Exception:
        logger.exception("Failed to fetch economic calendar")
        raise HTTPException(
            status_code=500, detail="Failed to fetch economic calendar data"
        )


@app.get("/api/timeseries", response_model=List[Timeseries])
async def get_timeseries():
    """
    Retrieve all timeseries data.
    """
    try:
        return Timeseries.find().run()
    except Exception:
        logger.exception("Failed to fetch timeseries data")
        raise HTTPException(status_code=500, detail="Failed to fetch timeseries data")

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


class UploadData(BaseModel):
    date: str
    code: str
    value: float


@app.post("/api/upload_data", status_code=status.HTTP_200_OK)
async def upload_data(payload: List[Dict[str, Any]]):
    """
    - Accepts a JSON list in the request body, requiring 'date', 'code', and 'value' columns.
    - Converts to a Pandas DataFrame, pivots, and saves each timeseries to the DB.
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

        # Convert 'value' to numeric, coercing errors to NaN
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        # Drop rows where 'value' is NaN
        df = df.dropna(subset=["value"])
        # Convert 'date' to datetime, coercing errors to NaT
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Drop rows where 'date' or 'code' is missing
        df = df.dropna(subset=["date", "code"])

        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid records to upload after cleaning.",
            )

        # Pivot the DataFrame so each code becomes a column, indexed by date
        pivoted = (
            df.pivot(index="date", columns="code", values="value")
            .sort_index()
            .dropna(how="all", axis=1)
            .dropna(how="all", axis=0)
        )
        pivoted.index = pd.to_datetime(pivoted.index)

        updated_codes = []
        for code in pivoted.columns:
            ts = Timeseries.find_one({"code": code}).run()
            if ts is None:
                continue
            # Store as a Series with date index and float values
            series = pivoted[code].dropna()
            # Convert index to Python date objects for consistent storage
            ts.data = series
            updated_codes.append(code)

        return {
            "message": f"Successfully received {len(df)} records.",
            "updated_codes": updated_codes,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process data upload")
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/trigger_daily_task")
async def trigger_daily_task():
    """Manual trigger for the daily task."""
    try:
        await run_daily_task()
        return {"status": "Daily task executed successfully"}
    except Exception:
        logger.exception("Failed to trigger daily task")
        raise HTTPException(status_code=500, detail="Failed to execute daily task")


from ix.db.query import *
from typing import Dict, List, Optional, Any, Union
from fastapi import Query, HTTPException, status
from datetime import datetime, date


# add at top if not present
import re, json
from typing import List, Dict, Any, Optional

# numpy, pandas, etc. already imported in your file


# --- helper: parse ["KEY=VALUE", "K=V"] or "KEY=VALUE,K=V" or even a JSON array string ---
def _parse_params_list(params: Optional[List[str]]) -> Dict[str, Any]:
    """
    Parse parameter lists in various formats:
    - ["SORT=FALSE", "HEADER=TRUE"]
    - ["KEY=VALUE,K=V"]
    - JSON array string: '["SORT=FALSE", "HEADER=TRUE"]'
    - Comma-separated: "SORT=FALSE,HEADER=TRUE"
    """
    out: Dict[str, Any] = {}
    if not params:
        return out

    def coerce(v: str) -> Any:
        """Convert string values to appropriate Python types."""
        v_stripped = v.strip().strip("'\"")
        vu = v_stripped.upper()
        if vu in ("TRUE", "YES", "1"):
            return True
        if vu in ("FALSE", "NO", "0"):
            return False
        if re.fullmatch(r"[-+]?\d+", v_stripped):
            try:
                return int(v_stripped)
            except Exception:
                pass
        if re.fullmatch(r"[-+]?\d*\.\d+", v_stripped):
            try:
                return float(v_stripped)
            except Exception:
                pass
        return v_stripped

    for raw in params:
        if raw is None:
            continue

        items: List[str] = []
        raw = raw.strip()

        # Handle JSON array string format: '["SORT=FALSE", "HEADER=TRUE"]'
        if raw.startswith("[") and raw.endswith("]"):
            try:
                arr = json.loads(raw)
                if isinstance(arr, list):
                    items.extend([str(item) for item in arr])
            except Exception:
                # If JSON parsing fails, treat as a regular string
                pass

        # If no items from JSON parsing, split on commas
        if not items:
            # Handle comma-separated values: "SORT=FALSE,HEADER=TRUE"
            items = [item.strip() for item in raw.split(",") if item.strip()]

        # Parse each key=value pair
        for kv in items:
            if not kv or "=" not in kv:
                continue
            try:
                k, v = kv.split("=", 1)
                k = k.strip().upper()
                out[k] = coerce(v)
            except Exception as e:
                logger.warning(f"Failed to parse parameter '{kv}': {e}")
                continue

    return out


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
    # Enhanced parameter support for various formats
    params: Optional[List[str]] = Query(
        None,
        alias="PARAMS",
        description=(
            "List of KEY=VALUE flags in various formats. Examples: "
            '["SORT=FALSE"], ["SORT=DESC,INCLUDE_INDEX=TRUE"], '
            '"SORT=FALSE". '
            "Supported flags: "
            "INCLUDE_INDEX=TRUE|FALSE (include date/index column in response), "
            "SORT=ASC|DESC or SORT=TRUE|FALSE (TRUE means descending), "
            "FORMAT=JSON|CSV (response format - future use)."
        ),
    ),
):
    """
    Enhanced series endpoint that handles various index types (string, float, datetime),
    with flexible PARAMS supporting multiple input formats and comprehensive flags.

    Example usage:
    - /api/series?series=GDP&params=["SORT=FALSE", "INCLUDE_HEADERS=TRUE"]
    - /api/series?series=GDP&params="SORT=DESC,INCLUDE_INDEX=TRUE"
    - /api/series?series=GDP&params=SORT=FALSE&params=INCLUDE_INDEX=TRUE
    """
    print(f"Params got = {params}")

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
                for col_name in ser.columns:
                    col_series = ser[col_name].copy()
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

    # Parse parameter flags; keep user's overrides
    flags = _parse_params_list(params)
    logger.info(f"Parsed parameter flags: {flags}")

    # === Set new defaults ONLY if not set by user ===
    if "SORT" not in flags:
        flags["SORT"] = "ASC"  # default: descending (latest first)
    if "INCLUDE_INDEX" not in flags:
        flags["INCLUDE_INDEX"] = True

    # Continue to extract flags (now using your defaulted "flags" dict)
    include_index_flag = bool(flags.get("INCLUDE_INDEX", False))
    format_flag = str(flags.get("FORMAT", "JSON")).upper()

    # Handle SORT parameter as before
    ascending = True
    sort_requested = False
    sort_val = flags.get("SORT", None)


    if sort_val is not None:
        sort_requested = True
        try:
            if isinstance(sort_val, bool):
                # TRUE => descending, FALSE => ascending
                ascending = not sort_val
            elif isinstance(sort_val, str):
                s = sort_val.strip().upper()
                if s == "DESC":
                    ascending = False
                elif s == "ASC":
                    ascending = True
                elif s == "TRUE":
                    ascending = (
                        False  # TRUE means descending for backward compatibility
                    )
                elif s == "FALSE":
                    ascending = True  # FALSE means ascending
                else:
                    raise ValueError("SORT must be ASC|DESC or TRUE|FALSE")
            else:
                raise ValueError("SORT must be ASC|DESC or TRUE|FALSE")

            # Sort the dataframe
            df = df.sort_index(ascending=ascending)
            logger.info(f"Applied sorting: ascending={ascending}")

        except Exception as e:
            logger.error(f"Failed to sort by index: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SORT flag: {str(e)}",
            )

    # Prepare the response payload
    payload = _prepare_response_payload(
        df,
        include_index=include_index_flag,
    )

    # Future: handle different output formats
    if format_flag == "CSV":
        # This could be implemented to return CSV format
        # For now, log the request and continue with JSON
        logger.info("CSV format requested but not yet implemented, returning JSON")

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
    df: pd.DataFrame,
    include_index: bool = False,
) -> Dict[str, Any]:
    """
    Prepare the response payload based on the parameters.

    Args:
        df: DataFrame to process
        include_index: Whether to include date/index column in output
    """
    try:
        # Replace NaN values with None for JSON serialization
        df = df.replace({np.nan: None, pd.NaT: None})

        payload = {}

        if include_index:
            # Convert index to string format for consistent JSON serialization
            if isinstance(df.index, pd.DatetimeIndex):
                index_data = df.index.strftime("%Y-%m-%d").tolist()
            else:
                # Convert other index types to string
                index_data = df.index.astype(str).tolist()

            payload["Idx"] = index_data

        # Add series data
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
