from fastapi import APIRouter, HTTPException, status
from bson.errors import InvalidId
from bunnet import PydanticObjectId
from ix import db
from ix.misc import yesterday, as_date
from dateutil import parser
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])

# Constants for tickers used in performance groups
PERFORMANCE_GROUP_TICKERS = {
    "local-indices": {
        "SPX Index": "S&P500",
        "INDU Index": "DJIA30",
        "CCMP Index": "NASDAQ",
        "RTY Index": "Russell2",
        "SX5E Index": "Stoxx50",
        "UKX Index": "FTSE100",
        "NKY Index": "Nikkei225",
        "KOSPI Index": "Kospi",
        "SHCOMP Index": "SSE",
    },
    "global-markets": {
        "ACWI": "ACWI",
        "IDEV": "DMxUS",
        "FEZ": "Europe",
        "EWJ": "Japan",
        "EWY": "Korea",
        "VWO": "Emerging",
        "VNM": "Vietnam",
        "INDA": "India",
        "EWZ": "Brazil",
    },
    "us-gics": {
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
    },
    "styles": {
        "MTUM": "Mtum",
        "QUAL": "Quality",
        "SIZE": "Size",
        "USMV": "MinVol",
        "VLUE": "Value",
        "IWO": "Small G",
        "IWN": "Small V",
        "IWM": "Small",
    },
    "global-bonds": {
        "AGG": "Agg",
        "SHY": "T 1-3Y",
        "IEF": "T 3-7Y",
        "TLH": "T 10-20Y",
        "TLT": "T 20+Y",
        "LQD": "I Grade",
        "HYG": "High Yield",
        "EMB": "Emerging",
    },
    "currency": {
        "DXY Index": "DXY",
        "USDEUR": "EUR",
        "USDGBP": "GBP",
        "USDJPY": "JPY",
        "USDKRW": "KRW",
        "XBTUSD": "Bitcoin",
    },
    "commodities": {
        "GC1 Comdty": "Gold",
        "SI1 Comdty": "Silver",
        "HG1 Comdty": "Copper",
        "CL1 Comdty": "WTI",
    },
    "theme": {
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
    },
}


# Utility function for handling database retrieval errors
def handle_db_exception(error_msg: str):
    def inner(exc: Exception):
        print(exc)  # Log the exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{error_msg}: {str(exc)}",
        )

    return inner


@router.get("/strategies", response_model=list[db.Strategy])
async def get_strategies():
    try:
        strategies = db.Strategy.find_all().to_list()
        return [
            db.Strategy(**strategy.model_dump(exclude={"book"}))
            for strategy in strategies
        ]
    except Exception as e:
        handle_db_exception("Error fetching strategies")(e)


@router.get("/strategies/{id}", response_model=db.Strategy)
async def get_strategy_by_id(id: str):
    try:
        strategy = db.Strategy.find_one(db.Strategy.id == PydanticObjectId(id)).run()
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
            )
        return strategy
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid strategy ID format"
        )
    except Exception as e:
        handle_db_exception("Error fetching strategy by ID")(e)


@router.get("/economic_calendar", response_model=list[db.EconomicCalendar])
async def get_economic_calendar():
    try:
        return db.EconomicCalendar.find_all().to_list()
    except Exception as e:
        handle_db_exception("Error fetching economic calendar")(e)


@router.get("/regimes", response_model=list[db.Regime])
async def get_regimes():
    try:
        regimes = db.Regime.find_all().to_list()
        if not regimes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Regimes not found"
            )
        return regimes
    except Exception as e:
        handle_db_exception("Error fetching regimes")(e)


@router.get("/insights/{id}", response_model=db.Insight)
async def get_insight_by_id(id: str):
    try:
        insight = db.Insight.find_one(db.Insight.id == PydanticObjectId(id)).run()
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return insight
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid insight ID format"
        )
    except Exception as e:
        handle_db_exception("Error fetching insight by ID")(e)


@router.get("/insights", response_model=list[db.Insight])
async def get_insights():
    try:
        return db.Insight.find_all().to_list()
    except Exception as e:
        handle_db_exception("Error fetching insights")(e)


class StrategySummary(BaseModel):
    code: str
    last_updated: str | None = None
    ann_return: float | None = None
    ann_volatility: float | None = None
    nav_history: list[float] | None = None


@router.get("/strategies/summary", response_model=list[StrategySummary])
async def get_strategies_summary():
    try:
        strategies = db.Strategy.find_all().to_list()
        if not strategies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Strategies not found"
            )
        return [StrategySummary(**strategy.model_dump()) for strategy in strategies]
    except Exception as e:
        handle_db_exception("Error fetching strategies summary")(e)


class StrategyPerformanceData(BaseModel):
    d: list[str]
    v: list[float]
    b: list[float]


@router.get("/strategies/{code}/performance", response_model=StrategyPerformanceData)
async def get_strategy_performance(code: str):
    try:
        strategy = db.Strategy.find_one(db.Strategy.code == code).run()
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
            )
        return StrategyPerformanceData(
            d=strategy.book.d, v=strategy.book.v, b=strategy.book.b
        )
    except Exception as e:
        handle_db_exception("Error fetching strategy performance")(e)


@router.get("/pxlast")
async def get_all_pxlast():
    try:
        data = db.get_pxs().loc["2020":].stack().reset_index()
        data.columns = ["date", "code", "value"]
        return data.to_dict("records")
    except Exception as e:
        handle_db_exception("Error fetching PX last data")(e)


@router.get("/performance", response_model=list[db.KeyPerformance])
async def get_performance(group: str = "local-indices", asofdate: str | None = None):
    try:
        asofdate = asofdate or as_date(yesterday())
        tickers = PERFORMANCE_GROUP_TICKERS.get(group)
        if not tickers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid group"
            )

        performances = []
        for key, name in tickers.items():
            performance = db.Performance.find_one(
                db.Performance.code == key,
                db.Performance.date == parser.parse(asofdate).date(),
            ).run()
            if performance:
                performance.code = name
                performances.append(performance)

        return performances
    except Exception as e:
        handle_db_exception("Error fetching performance data")(e)
