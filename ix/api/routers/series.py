


from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ix.misc.terminal import get_logger
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import pandas as pd
import numpy as np

logger = get_logger(__name__)
router = APIRouter()


class DateUtils:
    """Utility class for date-related operations."""

    @staticmethod
    def normalize_index(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame index to handle various index types.

        Args:
            df: DataFrame with potentially mixed index types

        Returns:
            DataFrame with normalized datetime index where possible
        """
        if isinstance(df.index, pd.DatetimeIndex):
            return df

        try:
            # Handle string indices
            if df.index.dtype == "object":
                df.index = pd.to_datetime(df.index, errors='coerce')
                if df.index.isna().any():
                    logger.warning("Some dates could not be converted, keeping original index")
                    return df

            # Handle numeric indices (Excel serial dates, timestamps)
            elif df.index.dtype in ["int64", "float64"]:
                numeric_values = df.index.values

                # Excel serial numbers (1-100000 range)
                if np.all((numeric_values >= 1) & (numeric_values <= 100000)):
                    base_date = pd.Timestamp("1900-01-01")
                    df.index = pd.to_datetime(
                        base_date + pd.to_timedelta(numeric_values - 1, unit="D")
                    )
                # Unix timestamps in seconds
                elif np.all((numeric_values >= 946684800) & (numeric_values <= 4102444800)):
                    df.index = pd.to_datetime(numeric_values, unit="s")
                # Unix timestamps in milliseconds
                elif np.all((numeric_values >= 946684800000) & (numeric_values <= 4102444800000)):
                    df.index = pd.to_datetime(numeric_values, unit="ms")

        except Exception as e:
            logger.warning(f"Could not normalize index: {e}")

        return df

    @staticmethod
    def apply_date_filter(df: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        """Apply date filtering to DataFrame."""
        if not isinstance(df.index, pd.DatetimeIndex):
            return df

        try:
            if start:
                start_date = pd.to_datetime(start)
                df = df.loc[df.index >= start_date]

            if end:
                end_date = pd.to_datetime(end)
                df = df.loc[df.index <= end_date]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}"
            )

        return df

class SeriesQueryParams(BaseModel):
    """Model for series query parameters."""
    series: List[str] = Field(..., min_items=1)
    start: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}-\d{2}$')
    end: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}-\d{2}$')
    include_dates: bool = False



@router.get(
    "/series",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, List[Any]],
    summary="Query series data",
    description="Query one or more series by code with optional date filtering"
)
async def get_series(
    series: List[str] = Query(..., description="Series codes or aliases (format: alias=code)"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_dates: bool = Query(False, description="Include date column in response")
):
    """
    Query one or more series by code.

    Supports aliasing with format: alias=code
    Returns data optionally filtered by date range.
    """
    try:
        frames = []

        for spec in series:
            # Parse alias and code
            if "=" in spec:
                alias, code = spec.split("=", 1)
                alias, code = alias.strip(), code.strip()
            else:
                alias = code = spec.strip()

            try:
                # Evaluate the series code
                result = eval(code)

                if isinstance(result, pd.DataFrame):
                    # Add all DataFrame columns as separate series
                    for col_name in result.columns:
                        col_series = result[col_name].copy()
                        col_series.name = f"{alias}_{col_name}" if alias != code else col_name
                        frames.append(col_series)

                elif isinstance(result, pd.Series):
                    result = result.copy()
                    result.name = alias
                    frames.append(result)
                else:
                    raise ValueError(f"Expected Series or DataFrame, got {type(result)}")

            except Exception as e:
                logger.error(f"Error processing series '{code}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid series code '{code}': {str(e)}"
                )

        if not frames:
            return {}

        # Combine all series
        df = pd.concat(frames, axis=1)
        df = DateUtils.normalize_index(df)
        df = df.dropna(how="all")

        if df.empty:
            return {}

        # Apply date filtering
        df = DateUtils.apply_date_filter(df, start, end)

        if df.empty:
            return {}

        # Prepare response
        df = df.replace({np.nan: None, pd.NaT: None})

        if include_dates:
            if isinstance(df.index, pd.DatetimeIndex):
                df.index = df.index.strftime("%Y-%m-%d")
            df = df.sort_index().reset_index()
            df = df.rename(columns={df.columns[0]: "date"})
            return df.to_dict("list")
        else:
            return {col: df[col].tolist() for col in df.columns}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process series query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process series query: {str(e)}"
        )
