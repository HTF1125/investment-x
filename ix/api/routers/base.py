from typing import List
from typing import Type
from typing import Optional
from bunnet import Document
from ix.db.conn import Code
from bson import ObjectId
from pydantic import BaseModel
from typing import Dict
from datetime import date
from fastapi import Query
from fastapi import APIRouter, BackgroundTasks, status
from fastapi import HTTPException, Body
from ix.db import Metadata, InsightSource, InsightSourceBase, Performance, IndexGroup
from ix import task


def get_model_codes(model: Type[Document]) -> List[str]:

    if getattr(model, "code") is None:
        raise Exception(f"Document {model.__name__} does not have code attribute.")

    codes = [
        str(doc.code)
        for doc in model.find_all(
            projection_model=Code,
        ).run()
    ]
    return codes


router = APIRouter(prefix="", tags=["metadata"])


@router.get(
    "/metadatas",
    response_model=List[Metadata],
    status_code=status.HTTP_200_OK,
)
def get_metadatas():
    try:
        metadatas = Metadata.find_all().run()
        if not metadatas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return metadatas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.get(
    "/metadata",
    status_code=status.HTTP_201_CREATED,
    description="Get ticker code",
)
def get_metadata(
    id: Optional[str] = Query(None, description="MetaData id (optional)"),
    code: Optional[str] = Query(None, description="MetaData code (optional)"),
):
    if code:
        metadata = Metadata.find_one(Metadata.code == code).run()
    elif id:
        metadata = Metadata.find_one(Metadata.id == id).run()
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metadatas found.",
        )
    return metadata


@router.delete(
    "/metadata",
    status_code=status.HTTP_200_OK,
    description="Add a new ticker code to the database.",
)
def delete_metata(metadata: Metadata):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(metadata.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    Metadata.find_one(Metadata.id == metadata.id).delete().run()
    return {"message": "InsightSource deleted successfully"}


@router.put(
    "/metadata",
    status_code=status.HTTP_200_OK,
    response_model=Metadata,
    description="Add a new ticker code to the database.",
)
def update_metadata(metadata: Metadata):

    if not ObjectId.is_valid(metadata.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    try:
        _metadata = Metadata.find_one(Metadata.id == metadata.id).run()
        if not _metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return _metadata.set(metadata.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.post(
    "/metadata",
    status_code=status.HTTP_200_OK,
    response_model=Metadata,
    description="Add a new ticker code to the database.",
)
def create_metadata(metadata: Metadata):

    try:
        return metadata.create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


# Define the request model for the data
class TimeSeriesData(BaseModel):
    data: Dict[date, float]  # Dictionary with date as key and float as value


# Add the route to the router
@router.get("/timeseries")
async def get_timeseries(
    code: str = Query(..., description="MetaData code"),
    field: str = Query("PX_LAST", description="Field code"),
):
    """
    Endpoint to update time series data.

    Parameters:
        - code (str): Code of the time series (query parameter).
        - field (str): Field to update (query parameter).
        - body (TimeSeriesData): Time series data in the request body.
    """
    try:
        metadata = Metadata.find_one(Metadata.code == code).run()
        if metadata is None:
            raise
        return metadata.ts(field=field).data.to_dict()
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    path="/timeseries",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def update_timeseries(
    code: str = Query(..., description="Code of the time series"),
    field: str = Query(..., description="Field to update"),
    body: TimeSeriesData = Body(..., description="Time series data"),
):
    """
    Endpoint to update time series data.

    Parameters:
        - code (str): Code of the time series (query parameter).
        - field (str): Field to update (query parameter).
        - body (TimeSeriesData): Time series data in the request body.
    """
    metadata = Metadata.find_one(Metadata.code == code).run()
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"MetaData<{code}> not found.")
    try:
        metadata.ts(field=field).data = body.data
        return {"message": "Time series updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    path="/signals",
    response_model=List[Metadata],
    status_code=status.HTTP_200_OK,
)
async def get_signals():
    try:
        metadatas = Metadata.find_many(Metadata.market == "Signal").run()
        if not metadatas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return metadatas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.get(
    path="/insightsources",
    response_model=List[InsightSource],
    status_code=status.HTTP_200_OK,
)
async def get_insight_sources():
    try:
        insight_souces = InsightSource.find_all().run()
        if not insight_souces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return insight_souces
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.post(
    path="/insightsources",
    response_model=InsightSource,
    status_code=status.HTTP_201_CREATED,
)
async def create_insight_source(insight_source: InsightSourceBase = Body(...)):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    try:
        model = {}
        for k, v in insight_source.model_dump().items():
            if v is not None:
                model[k] = v
        return InsightSource(**model).create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.put(
    path="/insightsources",
    response_model=InsightSource,
    status_code=status.HTTP_200_OK,
)
async def update_insight_source(
    update_insight_source: InsightSource = Body(...),
):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(update_insight_source.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    update = {key: value for key, value in update_insight_source.model_dump().items()}
    if not update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    try:
        insight_source = InsightSource.find_one(
            InsightSource.id == update_insight_source.id
        ).run()
        if not insight_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return insight_source.set(update)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.delete(
    path="/insightsources/{id}",
    status_code=status.HTTP_200_OK,
)
async def delete_insight_source(id: str):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    InsightSource.find_one(InsightSource.id == ObjectId(id)).delete().run()
    return {"message": "InsightSource deleted successfully"}


# The route that will trigger the background task
@router.get(path="/tasks/daily", status_code=status.HTTP_200_OK)
async def ping_task_daily(background_tasks: BackgroundTasks):
    """
    _summary_

    _extended_summary_

    Args:
        background_tasks (BackgroundTasks): _description_
    """

    async def run_daily_task():
        task.run()

    background_tasks.add_task(run_daily_task)
    return {"message": "Task is running in the background"}


@router.get(
    path="/performance",
    response_model=Performance,
    status_code=status.HTTP_200_OK,
)
def get_performance_by_code(code: str):
    """
    _summary_

    _extended_summary_
    """
    try:
        performance = Performance.find_one({"group": code}).run()
        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No performances found.",
            )
        return performance
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching performances: {str(e)}",
        )


@router.get(
    path="/performance",
    response_model=List[Performance],
    status_code=status.HTTP_200_OK,
)
def get_performance():
    """
    _summary_

    _extended_summary_
    """
    try:
        performances = Performance.find_all().run()
        if not performances:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No performances found.",
            )
        return performances
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching performances: {str(e)}",
        )


from pydantic import BaseModel
from ix.misc.date import today
from datetime import date


class PerforamnceGrouped(BaseModel):
    group: str
    code: str
    name: Optional[str] = None
    level: Optional[float] = None
    pct_chg_1d: Optional[float] = None
    pct_chg_1w: Optional[float] = None
    pct_chg_1m: Optional[float] = None
    pct_chg_3m: Optional[float] = None
    pct_chg_6m: Optional[float] = None
    pct_chg_1y: Optional[float] = None
    pct_chg_3y: Optional[float] = None
    pct_chg_mtd: Optional[float] = None
    pct_chg_ytd: Optional[float] = None


@router.get(
    path="/performances-grouped",
    response_model=List[PerforamnceGrouped],
    status_code=status.HTTP_200_OK,
)
def get_performance_grouped():

    groups = [
        {"group": "LocalIndices", "code": "^SPX", "name": "S&P500"},
        {"group": "LocalIndices", "code": "^INDU", "name": "DJIA30"},
        {"group": "LocalIndices", "code": "^CCMP", "name": "NASDAQ"},
        {"group": "LocalIndices", "code": "^RTY", "name": "Russell2"},
        {"group": "LocalIndices", "code": "^SX5E", "name": "Stoxx50"},
        {"group": "LocalIndices", "code": "^UKX", "name": "FTSE100"},
        {"group": "LocalIndices", "code": "^NKY", "name": "Nikkei225"},
        {"group": "LocalIndices", "code": "^KOSPI", "name": "Kospi"},
        {"group": "LocalIndices", "code": "^SHCOMP", "name": "SSE"},
        {"group": "GlobalMarkets", "code": "ACWI", "name": "ACWI"},
        {"group": "GlobalMarkets", "code": "IDEV", "name": "DMxUS"},
        {"group": "GlobalMarkets", "code": "FEZ", "name": "Europe"},
        {"group": "GlobalMarkets", "code": "EWJ", "name": "Japan"},
        {"group": "GlobalMarkets", "code": "EWY", "name": "Korea"},
        {"group": "GlobalMarkets", "code": "VWO", "name": "Emerging"},
        {"group": "GlobalMarkets", "code": "VNM", "name": "Vietnam"},
        {"group": "GlobalMarkets", "code": "INDA", "name": "India"},
        {"group": "GlobalMarkets", "code": "EWZ", "name": "Brazil"},
        {"group": "Sectors-US", "code": "XLB", "name": "Materi."},
        {"group": "Sectors-US", "code": "XLY", "name": "Cycl"},
        {"group": "Sectors-US", "code": "XLF", "name": "Fin."},
        {"group": "Sectors-US", "code": "XLRE", "name": "Estate."},
        {"group": "Sectors-US", "code": "XLC", "name": "Comm."},
        {"group": "Sectors-US", "code": "XLE", "name": "Energy"},
        {"group": "Sectors-US", "code": "XLI", "name": "Indus."},
        {"group": "Sectors-US", "code": "XLK", "name": "I.Tech"},
        {"group": "Sectors-US", "code": "XLP", "name": "Non-Cycl"},
        {"group": "Sectors-US", "code": "XLV", "name": "Health"},
        {"group": "Sectors-US", "code": "XLU", "name": "Util"},
        {"group": "Styles", "code": "MTUM", "name": "Mtum"},
        {"group": "Styles", "code": "QUAL", "name": "Quality"},
        {"group": "Styles", "code": "SIZE", "name": "Size"},
        {"group": "Styles", "code": "USMV", "name": "MinVol"},
        {"group": "Styles", "code": "VLUE", "name": "Value"},
        {"group": "Styles", "code": "IWO", "name": "Small G"},
        {"group": "Styles", "code": "IWN", "name": "Small V"},
        {"group": "Styles", "code": "IWM", "name": "Small"},
        {"group": "GlobalBonds", "code": "AGG", "name": "Agg"},
        {"group": "GlobalBonds", "code": "SHY", "name": "T 1-3Y"},
        {"group": "GlobalBonds", "code": "IEF", "name": "T 3-7Y"},
        {"group": "GlobalBonds", "code": "TLH", "name": "T 10-20Y"},
        {"group": "GlobalBonds", "code": "TLT", "name": "T 20+Y"},
        {"group": "GlobalBonds", "code": "LQD", "name": "I Grade"},
        {"group": "GlobalBonds", "code": "HYG", "name": "High Yield"},
        {"group": "GlobalBonds", "code": "EMB", "name": "Emerging"},
        {"group": "Currencies", "code": "^DXY", "name": "DXY"},
        {"group": "Currencies", "code": "USDEUR", "name": "EUR"},
        {"group": "Currencies", "code": "USDGBP", "name": "GBP"},
        {"group": "Currencies", "code": "USDJPY", "name": "JPY"},
        {"group": "Currencies", "code": "USDKRW", "name": "KRW"},
        {"group": "Commodities", "code": "GSG", "name": "Broad"},
        {"group": "Commodities", "code": "IAU", "name": "Gold"},
        {"group": "Commodities", "code": "SLV", "name": "Silver"},
        {"group": "Commodities", "code": "HG1 Comdty", "name": "Copper"},
        {"group": "Commodities", "code": "CL1 Comdty", "name": "WTI"},
        {"group": "Commodities", "code": "XBTUSD", "name": "Bitcoin"},
        {"group": "Themes", "code": "UFO", "name": "Space"},
        {"group": "Themes", "code": "VNQ", "name": "REITs"},
        {"group": "Themes", "code": "PPH", "name": "Pharma"},
        {"group": "Themes", "code": "PAVE", "name": "Pave"},
        {"group": "Themes", "code": "SRVR", "name": "Data/Infra"},
        {"group": "Themes", "code": "FINX", "name": "FinTech"},
        {"group": "Themes", "code": "TAN", "name": "Solar"},
        {"group": "Themes", "code": "LIT", "name": "Lit/Battery"},
        {"group": "Themes", "code": "SKYY", "name": "Cloud"},
        {"group": "Themes", "code": "DRIV", "name": "EV/Drive"},
        {"group": "Themes", "code": "SNSR", "name": "IoT"},
        {"group": "Themes", "code": "SOXX", "name": "Semis"},
    ]

    for group in groups:
        performance = Performance.find_one(Performance.code == group["code"]).run()
        if performance:
            group.update(performance.model_dump())

    return groups


from ix.db import TacticalView


@router.get(
    path="/tacticalview",
    response_model=TacticalView,
    status_code=status.HTTP_200_OK,
)
def get_tacticalview():
    """
    _summary_

    _extended_summary_
    """
    # Find the most recent document by sorting published_date descending
    most_recent = TacticalView.find_one(
        {},  # Match all documents
        sort=[("published_date", -1)],  # Sort descending by `published_date`
    ).run()

    if not most_recent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No TacticalView found"
        )

    # Return the most recent TacticalView
    return most_recent


from ix.db import Insight
from ix.misc import onemonthbefore


def fetch_insights(
    start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[Insight]:
    """
    Fetch insights from the database based on a date range.

    Args:
        start_date (Optional[date]): Start date (inclusive). Defaults to None (no lower bound).
        end_date (Optional[date]): End date (exclusive). Defaults to None (no upper bound).

    Returns:
        List[ix.Insight]: List of insights matching the query.
    """
    query = {}
    if start_date:
        query.setdefault("published_date", {})["$gte"] = start_date
    if end_date:
        query.setdefault("published_date", {})["$lt"] = end_date

    try:
        return Insight.find(query).to_list()
    except Exception as e:
        return []


import json
from ix.misc.openai import TaaViews
from ix.misc.settings import Settings


# @router.get(
#     path="/tacticalview/refresh",
#     response_model=TacticalView,
#     status_code=status.HTTP_200_OK,
# )
# def update_tacticalview():
#     """
#     _summary_

#     _extended_summary_
#     """
#     insights = fetch_insights(start_date=onemonthbefore().date())
#     txt = "\n".join(
#         f"{insight.published_date} : {insight.summary}"
#         for insight in insights
#         if insight.summary
#     )
#     views = TaaViews(api_key=Settings.openai_secret_key).generate_tactical_views(
#         insights=txt
#     )

#     # Ensure the JSON string ends properly
#     if "}" in views:
#         views = views[: views.rfind("}") + 1]  # Truncate at the last closing brace

#     print("Cleaned JSON String:", views)
#     try:
#         # Load the JSON data

#         data = json.loads(views)
#         print("Parsed JSON:", data)
#         TacticalView(views=data, published_date=ix.misc.now()).create()
#     except json.JSONDecodeError as e:
#         print("JSONDecodeError:", e.msg)
#         print("Problematic Location:", e.pos)


from ix.db import MarketCommentary


@router.get(
    path="/market_commentary",
    response_model=MarketCommentary,
    status_code=status.HTTP_200_OK,
)
def get_market_commentary(
    asofdate: Optional[date] = None,
    frequency: str = "Daily",
):
    # Construct query filters

    if asofdate:
        # Query for the commentary based on filters
        commentary = MarketCommentary.find_one(
            {"asofdate": asofdate, "frequency": frequency}
        ).run()
        if commentary:
            return commentary
    commentary = MarketCommentary.find_one(
        {"frequency": frequency}, sort=[("asofdate", -1)]
    ).run()
    if commentary:
        return commentary
    # If no document is found, raise a 404 error
    error_detail = "No Market Commentary found"
    if asofdate:
        error_detail += f" for the date {asofdate}"
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail,
    )


class TimeSeriesPredicitonResponse(BaseModel):

    features: Dict[str, Dict[date, float]]
    target: Dict[date, float]
    prediction: Dict[date, float]


import pandas as pd


@router.get(
    path="/predictions",
    response_model=TimeSeriesPredicitonResponse,
    status_code=status.HTTP_200_OK,
)
def get_predictions(name: str):

    if name == "SPX_EPS_Forcastor_6M":
        from ix.core.pred.ts import SPX_EPS_Forcastor_6M

        model = SPX_EPS_Forcastor_6M().fit()
        start = "2020"
        features = model.features
        features.index += pd.offsets.MonthEnd(6)

        data = {
            "features": {
                feature: model.features[feature].loc[start:].dropna().to_dict()
                for feature in features
            },
            "target": model.target.loc[start:].to_dict(),
            "prediction": model.prediction.loc[start:].to_dict(),
        }
        return data
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )


from ix.db import Insight


@router.put(
    "/insight",
    response_model=Insight,
    status_code=status.HTTP_200_OK,
)
def put_insight(insight_new: Insight = Body(...)):

    if not ObjectId.is_valid(insight_new.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    insight = Insight.find_one(Insight.id == ObjectId(insight_new.id)).run()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
        )

    # Update the fields
    insight.set(insight_new.model_dump())

    return insight


import base64
from ix.db import Boto


class PDF(BaseModel):
    content: str


def generate_summary(content: bytes, insight: Insight):
    from ix.misc import PDFSummarizer, Settings

    summary = PDFSummarizer(Settings.openai_secret_key).process_insights(content)
    insight.set({"summary": summary})


@router.post(
    "/insight/frompdf",
    response_model=Insight,
    status_code=status.HTTP_200_OK,
)
def create_insight_with_pdf(
    background_tasks: BackgroundTasks,
    pdf: PDF = Body(...),
):
    """
    Adds a new Insight with the provided data.
    """

    try:
        content_bytes = base64.b64decode(pdf.content)
        insight = Insight().create()
        if content_bytes:
            Boto().save_pdf(
                pdf_content=content_bytes,
                filename=f"{insight.id}.pdf",
            )
            # background_tasks.add_task(generate_summary, content_bytes, insight)
        return insight
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Base64 content",
        )


@router.delete("/insight/{id}", status_code=status.HTTP_200_OK)
def delete_insight(id: str):
    """
    Deletes an Insight by its ID.

    """
    Insight.find_one(Insight.id == ObjectId(id)).delete().run()
    return {"message": "Insight deleted successfully"}


import re
from datetime import datetime


@router.get(
    "/insights",
    response_model=List[Insight],
    status_code=status.HTTP_200_OK,
)
def get_insights(
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(
        100, gt=0, description="Maximum number of records to return"
    ),
    search: Optional[str] = Query(
        None, description="Search term to filter insights by issuer, name, or date"
    ),
):
    """
    Retrieves insights sorted by date in descending order, with support for pagination and search.
    """
    try:
        # Base query
        query = {}

        if search:
            # Step 1: Try to extract a date from the search term using regex
            date_pattern = r"\d{4}-\d{2}-\d{2}"  # Match date in YYYY-MM-DD format
            date_match = re.search(date_pattern, search)

            # If a date is found, separate the date and text parts
            if date_match:
                search_date_str = date_match.group(0)
                try:
                    search_date = datetime.strptime(
                        search_date_str, "%Y-%m-%d"
                    )  # Convert to date object
                    query["published_date"] = {
                        "$eq": search_date
                    }  # Filter by exact date
                except ValueError:
                    pass  # If date format is incorrect, we ignore it

                # Remove the date part from the search term for text-based search
                search_text = search.replace(search_date_str, "").strip()
            else:
                # No date found, use the entire search term as text-based search
                search_text = search

            # Step 2: Handle the text-based search for issuer, name, and published_date
            if search_text:
                search_keywords = search_text.lower().split(sep="_")

                conditions = []
                for keyword in search_keywords:
                    conditions.append(
                        {
                            "$or": [
                                {"issuer": {"$regex": keyword, "$options": "i"}},
                                {"name": {"$regex": keyword, "$options": "i"}},
                                {
                                    "published_date": {
                                        "$regex": keyword,
                                        "$options": "i",
                                    }
                                },
                            ]
                        }
                    )

                query["$and"] = conditions

        # Fetch insights with the query
        insights = Insight.find(query).sort("-published_date").skip(skip).limit(limit)

        return list(insights)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching insights: {str(e)}",
        )


@router.post(
    "/insight/summarize/{id}",
    response_model=str,
    status_code=status.HTTP_200_OK,
)
def update_insight_summary(id: str):
    """
    Adds a new Insight with the provided data.
    """
    from ix.misc import PDFSummarizer, Settings
    from markitdown import MarkItDown

    insight = Insight.find_one(Insight.id == ObjectId(id)).run()
    if not insight:
        raise
    report = PDFSummarizer(Settings.openai_secret_key).process_insights(
        insight.get_content()
    )
    insight.set({"summary": report})
    return report
