from fastapi import APIRouter
from fastapi import Query
from fastapi import HTTPException
from bunnet import SortDirection
from ix import db
from ix.misc import last_business_day, as_date

router = APIRouter(prefix="/data", tags=["data"])


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


from bunnet import PydanticObjectId


from pydantic import BaseModel, Field
from datetime import date


@router.get("/pxlast")
async def get_all_pxlast():
    data = db.get_ts().loc["2020":].stack().reset_index()
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
