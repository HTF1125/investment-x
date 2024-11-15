from fastapi import APIRouter
from fastapi import Query
from fastapi import HTTPException
from fastapi import status
from bson.errors import InvalidId
from bunnet import PydanticObjectId, SortDirection
from ix import db
from ix.misc import last_business_day, as_date

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/signals", response_model=list[db.Signal])
def get_signals():
    return [
        db.Signal(**signal.model_dump(exclude={"book"}))
        for signal in db.Signal.find_all().run()
    ]


@router.get("/strategies", response_model=list[db.Strategy])
def get_strategies():
    return [
        db.Strategy(**strategy.model_dump(exclude={"book"}))
        for strategy in db.Strategy.find_all().run()
    ]


@router.get("/strategies/{id}", response_model=db.Strategy)
def get_strategy_by_id(id: str):
    try:

        # Attempt to retrieve the insight
        insight = db.Strategy.find_one(db.Strategy.id == PydanticObjectId(id)).run()

        if insight is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )

        return insight

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid insight ID format"
        )
    except Exception as e:
        print(e)
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(e)}",
        )


@router.get("/economic_calendar", response_model=list[db.EconomicCalendar])
async def get_economic_calendar() -> list[db.EconomicCalendar]:
    """
    Retrieve all economic calendar events.

    Returns:
        List[EconomicCalendarResponse]: A list of economic calendar events.

    Raises:
        HTTPException: If there's an error retrieving the data.
    """
    try:
        data = db.EconomicCalendar.find_all().to_list()
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving economic calendar: {str(e)}"
        )


@router.get("/regimes")
def get_regimes() -> list[db.Regime]:
    try:
        regimes_db = db.Regime.find_all().to_list()
        if not regimes_db:
            raise HTTPException(status_code=404, detail="No regimes found")
        return regimes_db
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving regimes: {str(e)}"
        )


from bunnet import PydanticObjectId


@router.get("/insights/{id}")
async def get_inisghts_by_id(id: str) -> db.Insight:

    try:

        # Attempt to retrieve the insight
        insight = db.Insight.find_one(db.Insight.id == PydanticObjectId(id)).run()

        if insight is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )

        return insight

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid insight ID format"
        )
    except Exception as e:
        print(e)
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(e)}",
        )


@router.put("/insights/{id}")
async def update_insight_by_id(id: str, insight_update: db.Insight) -> db.Insight:
    try:
        # Attempt to retrieve the existing insight
        existing_insight = db.Insight.find_one(
            db.Insight.id == PydanticObjectId(id)
        ).run()

        if existing_insight is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )

        # Prepare the updated insight
        updated_insight = existing_insight.copy(update=insight_update.dict())

        # Update the insight in the database
        db.Insight.update(
            {"_id": PydanticObjectId(id)}, {"$set": updated_insight}
        ).run()

        return updated_insight

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid insight ID format"
        )
    except Exception as e:
        print(e)
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(e)}",
        )


from pydantic import BaseModel, Field
from datetime import date


# Define a request model to validate the incoming data structure
class InsightCreateRequest(BaseModel):
    title: str
    date: date
    content: str


@router.post("/insights", status_code=200)
async def add_insight(payload: InsightCreateRequest):
    try:
        # Create a new insight entry
        insight_obj = db.Insight(
            title=payload.title,
            date=payload.date,
            content=payload.content,
        )

        # Insert the new insight into the database
        new_insight_id = insight_obj.create()

        if not new_insight_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create new insight",
            )

        # Retrieve the created insight to return it in the response
        created_insight = db.Insight.find_one(db.Insight.id == new_insight_id).run()
        return created_insight

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight: {str(e)}",
        )


@router.get("/insights")
def get_insights(
    skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)
) -> list[db.Insight]:
    # Fetch all insights and sort by date in descending order
    insights = (
        db.Insight.find_all()
        .skip(skip)
        .limit(limit)
        .sort([("date", SortDirection.DESCENDING)])
        .run()
    )
    return [
        db.Insight(**insight.model_dump(exclude={"content"}), content="")
        for insight in insights
    ]


@router.get("/pxlast")
async def get_all_pxlast():
    data = db.get_pxs().loc["2020":].stack().reset_index()
    data.columns = ["date", "code", "value"]
    return data.to_dict("records")


@router.get("/performance")
async def get_performance(
    group: str = "local-indices",
    asofdate: str | None = None,
) -> list[db.Performance]:

    if asofdate is None:
        asofdate = as_date(last_business_day())

    if group == "local-indices":
        # Example usage
        tickers = {
            "SPX Index": "S&P500",
            "INDU Index": "DJIA30",
            "CCMP Index": "NASDAQ",
            "RTY Index": "Russell2",
            "SX5E Index": "Stoxx50",
            "UKX Index": "FTSE100",
            "NKY Index": "Nikkei225",
            "KOSPI Index": "Kospi",
            "SHCOMP Index": "SSE",
        }
    elif group == "global-markets":

        tickers = {
            "ACWI": "ACWI",
            "IDEV": "DMxUS",
            "FEZ": "Europe",
            "EWJ": "Japan",
            "EWY": "Korea",
            "VWO": "Emerging",
            "VNM": "Vietnam",
            "INDA": "India",
            "EWZ": "Brazil",
        }

    elif group == "us-gics":

        tickers = {
            "XLB": "Materi.",
            "XLY": "Cycl",
            "XLF": "Fin.",
            "XLRE": "R.E.",
            "XLC": "Comm.",
            "XLE": "Energy",
            "XLI": "Indus.",
            "XLK": "I.Tech",
            "XLP": "Non-Cycl",
            "XLV": "Health",
            "XLU": "Util",
        }

    elif group == "styles":

        tickers = {
            "MTUM": "Mtum",
            "QUAL": "Quality",
            "SIZE": "Size",
            "USMV": "MinVol",
            "VLUE": "Value",
            "IWO": "Small G",
            "IWN": "Small V",
            "IWM": "Small",
        }

    elif group == "global-bonds":
        tickers = {
            "AGG": "Agg",
            "SHY": "T 1-3Y",
            "IEF": "T 3-7Y",
            "TLH": "T 10-20Y",
            "TLT": "T 20+Y",
            "LQD": "I Grade",
            "HYG": "High Yield",
            "EMB": "Emerging",
        }

    elif group == "currency":
        tickers = {
            "DXY Index": "DXY",
            "USDEUR": "EUR",
            "USDGBP": "GBP",
            "USDJPY": "JPY",
            "USDKRW": "KRW",
            "XBTUSD": "Bitcoin",
        }

    elif group == "commodities":
        tickers = {
            "GC1 Comdty": "Gold",
            "SI1 Comdty": "Silver",
            "HG1 Comdty": "Copper",
            "CL1 Comdty": "WTI",
        }

    elif group == "theme":
        tickers = {
            "UFO": "Space",
            "VNQ": "Real Estate",
            "PPH": "Pharma",
            "PAVE": "Pave",
            "SRVR": "Data/Infra",
            "FINX": "FinTech",
            "TAN": "Solar",
            "LIT": "Lit/Battery",
            "SKYY": "Cloud",
            "DRIV": "EV/Drive",
            "SNSR": "IoT",
            "SOXX": "Semis",
        }

    performances = []

    for key, name in tickers.items():
        performance = db.Performance.find_one(
            db.Performance.code == key,
        ).run()

        if performance is None:
            continue
        performance.code = name
        performances.append(performance)

    return performances
