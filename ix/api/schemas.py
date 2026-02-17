"""
Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date


# Authentication schemas
class Token(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""

    email: Optional[str] = None
    is_admin: bool = False


class UserLogin(BaseModel):
    """User login request schema."""

    email: EmailStr
    password: str
    remember_me: bool = False


class UserRegister(BaseModel):
    """User registration request schema."""

    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    disabled: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Timeseries schemas
class TimeseriesResponse(BaseModel):
    """Timeseries response schema."""

    id: str
    code: str
    name: Optional[str] = None
    provider: Optional[str] = None
    asset_class: Optional[str] = None
    category: Optional[str] = None
    start: Optional[date] = None
    end: Optional[date] = None
    num_data: Optional[int] = None
    source: Optional[str] = None
    source_code: Optional[str] = None
    frequency: Optional[str] = None
    unit: Optional[str] = None
    scale: Optional[int] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    remark: Optional[str] = None
    favorite: bool = False

    class Config:
        from_attributes = True


class TimeseriesCreate(BaseModel):
    """Timeseries create/update schema."""

    id: Optional[str] = None  # Optional ID for updating existing timeseries
    code: Optional[str] = (
        None  # Required for new timeseries, optional if id is provided
    )
    name: Optional[str] = None
    provider: Optional[str] = None
    asset_class: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    source_code: Optional[str] = None
    frequency: Optional[str] = None
    unit: Optional[str] = None
    scale: Optional[int] = 1
    currency: Optional[str] = None
    country: Optional[str] = None
    remark: Optional[str] = None
    favorite: Optional[bool] = False


class TimeseriesUpdate(BaseModel):
    """Timeseries update schema (all fields optional)."""

    code: Optional[str] = None  # Allows renaming a timeseries
    name: Optional[str] = None
    provider: Optional[str] = None
    asset_class: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    source_code: Optional[str] = None
    frequency: Optional[str] = None
    unit: Optional[str] = None
    scale: Optional[int] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    remark: Optional[str] = None
    favorite: Optional[bool] = None


class TimeseriesBulkUpdate(BaseModel):
    """Bulk timeseries update schema."""

    timeseries: List[TimeseriesCreate]


class TimeseriesDataPoint(BaseModel):
    """Timeseries data point schema."""

    date: str
    code: str
    value: float


class TimeseriesDataUpload(BaseModel):
    """Timeseries data upload schema."""

    data: List[TimeseriesDataPoint]


class TimeseriesColumnarUpload(BaseModel):
    """Columnar timeseries data upload - much more efficient for large datasets.

    Example payload:
    {
        "dates": ["2024-01-01", "2024-01-02", ...],
        "columns": {
            "CODE1": [1.23, 4.56, null, ...],
            "CODE2": [7.89, 0.12, null, ...]
        }
    }
    """

    dates: List[str]
    columns: Dict[str, List[Optional[float]]]


# Series schemas
class SeriesResponse(BaseModel):
    """Series response schema - column-oriented format."""

    Date: List[str]
    # Dynamic columns for series data
    # This will be handled as Dict[str, List[Any]]
