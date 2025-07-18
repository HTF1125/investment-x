import os
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, FileResponse

from ix.misc import get_logger
from ix.db import Timeseries, EconomicCalendar

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
        # update_economic_calendar()
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
    return Timeseries.find().to_list()


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
    frames: List[pd.Series] = []

    for spec in series:
        if "=" in spec:
            alias, code = spec.split("=", 1)
        else:
            alias, code = spec, spec

        try:
            ser = eval(code)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid series code '{code}': {e}",
            )

        if not isinstance(ser, pd.Series):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fetched object for '{code}' is not a pandas Series",
            )

        ser.name = alias
        frames.append(ser)

    if not frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid series provided"
        )

    df = pd.concat(frames, axis=1)
    df.index = pd.to_datetime(df.index)
    df = df.dropna(how="all")  # 모든 열이 NaN인 행 제거

    if start:
        df = df.loc[df.index >= pd.to_datetime(start)]
    if end:
        df = df.loc[df.index <= pd.to_datetime(end)]

    df = df.replace({np.nan: None})
    df.index = pd.to_datetime(df.index).strftime("%Y-%m-%d")
    if include_dates:
        df = df.sort_index().reset_index().rename(columns={"index": "Idx"})
        payload = df.to_dict(orient="list")
    else:
        payload = {col: df[col].tolist() for col in df.columns}

    return JSONResponse(content=payload)


def get_dates(
    start: Optional[str] = None,
    end: Optional[str] = None,
    frequency: str = "D",
    periods: Optional[int] = None,
) -> pd.DatetimeIndex:
    """
    Helper to build a DatetimeIndex via pandas.date_range.
    If periods is provided, at least one of start or end must be non-None.
    """
    if periods is not None and (start is None and end is None):
        raise ValueError(
            "If `periods` is specified, either `start` or `end` must be provided."
        )

    return pd.date_range(
        start=start,
        end=end,
        freq=frequency,
        periods=periods,
    )


# file: image_api.py
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image, ImageDraw


def create_sample_image() -> BytesIO:
    # (예시) 간단한 동적으로 생성된 이미지
    img = Image.new("RGB", (200, 100), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Hello, Excel!", fill=(255, 255, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


@app.get("/image")
def get_image():
    """
    PNG 포맷 이미지 스트림을 직접 반환
    """
    img_buf = create_sample_image()
    return StreamingResponse(img_buf, media_type="image/png")


from ix.db.query import *

@app.get("/api/query")
def _query(
    command: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    include_dates: bool = False,
):
    print(command)
    datas = eval(command)
    print(datas)
    datas = datas.replace(np.nan, None)
    datas.index = pd.to_datetime(datas.index).strftime("%Y-%m-%d")
    if start: datas = datas.loc[start:]
    if end: datas = datas.loc[:end]
    if include_dates:
        datas.index = pd.to_datetime(datas.index).strftime("%Y-%m-%d")
        datas = datas.reset_index()
    output = []
    for i in range(len(datas.columns)):
        output.append(datas.iloc[:, i].to_list())
    return output
