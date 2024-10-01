from fastapi import APIRouter
from fastapi import HTTPException
from ix.core.perf import get_period_performances
from ix import db

router = APIRouter(
    prefix="/data",
    tags=["data"],
)


@router.get("/tickers")
def get_tickers() -> list[db.Ticker]:
    tickers = db.Ticker.find_all().to_list()
    return tickers


@router.get("/ticker/{code}")
def get_ticker(code: str) -> db.Ticker:
    ticker = db.Ticker.find_one({"code": code}).run()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker not found")
    return ticker


# Define the POST route to add a new ticker
@router.post("/ticker/add", response_model=db.Ticker)
def add_ticker(ticker: db.Ticker):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": ticker.code})
    if existing_ticker:
        raise HTTPException(status_code=400, detail="Ticker already exists")
    db.Ticker.insert_one(ticker)
    return ticker


@router.post(
    "/ticker/update",
)
def mod_ticker(ticker: db.Ticker):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": ticker.code}).run()
    if not existing_ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")

    existing_ticker.set(ticker.model_dump())

    return {"message": "update complete"}


@router.post("/ticker/delete")
def del_ticker(code: str):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": code}).run()
    if not existing_ticker:
        raise HTTPException(status_code=400, detail="Ticker not found")
    db.Ticker.delete(existing_ticker)
    return {"message": f"Ticker with code {code} has been deleted successfully"}


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


@router.get("/pxlast")
async def get_all_pxlast():
    data = db.get_pxs().loc["2020":].stack().reset_index()
    data.columns = ["date", "code", "value"]
    return data.to_dict("records")


@router.get("/pxlast/{code}")
async def get_pxlast(code: str) -> db.Timeseries:
    ts = db.Timeseries.find_one({"code": code, "field": "PxLast"}).run()
    if not ts:
        raise HTTPException(
            status_code=404, detail=f"Ticker with code {code} not found"
        )
    return ts


@router.get("/performance")
async def get_performance(asofdate: str, group: str = "local-indicies") -> list[dict]:

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

    # Assuming 'ix' is your data source object
    pxs = db.get_pxs(tickers).dropna(how="all").loc[:asofdate]
    period_performances = get_period_performances(pxs=pxs).T.round(2)
    return period_performances.reset_index().to_dict("records")
