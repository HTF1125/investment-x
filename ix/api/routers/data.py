from fastapi import APIRouter
from fastapi import HTTPException
from ix import db
from ix.misc import as_date, last_business_day

router = APIRouter(
    prefix="/data",
    tags=["data"],
)


@router.get("/economic_calendar")
def get_economic_calendar() -> list[db.EconomicCalendar]:
    data = db.EconomicCalendar.find_all().to_list()
    return data


@router.get("/regimes")
def get_regimes() -> list[db.Regime]:
    regimes_db = db.Regime.find_all().run()
    if regimes_db:
        return regimes_db
    raise


from pydantic import BaseModel


class StrategySummary(BaseModel):
    code: str
    last_updated: str | None = None
    ann_return: float | None = None
    ann_volatility: float | None = None
    nav_history: list[float] | None = None


@router.get("/strategies/summary")
async def get_strategies_summary() -> list[StrategySummary]:
    strategies = db.Strategy.find_all().to_list()
    if not strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    out = []
    for strategy in strategies:
        out.append(StrategySummary(**strategy.model_dump()))
    return out


from pydantic import BaseModel


class StrategyPerformanceData(BaseModel):
    d: list[str]
    v: list[float]
    b: list[float]


@router.get("/strategies/{code}/performance", response_model=StrategyPerformanceData)
async def get_strategy_performance(code: str) -> StrategyPerformanceData:
    strategy = db.Strategy.find_one(db.Strategy.code == code).run()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyPerformanceData(
        d=strategy.book.d, v=strategy.book.v, b=strategy.book.b
    )


@router.get("/pxlast")
async def get_all_pxlast():
    data = db.get_pxs().loc["2020":].stack().reset_index()
    data.columns = ["date", "code", "value"]
    return data.to_dict("records")


@router.get("/performance")
async def get_performance(
    group: str = "local-indices",
    asofdate: str | None = None,
) -> list[db.KeyPerformance]:

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
    from dateutil import parser

    performances = []

    for key, name in tickers.items():
        performance = db.Performance.find_one(
            db.Performance.code == key,
            db.Performance.date == parser.parse(asofdate).date(),
        ).run()

        if performance is None:
            continue
        performance.code = name
        performances.append(performance)

    return performances
