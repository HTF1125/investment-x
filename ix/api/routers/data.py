from fastapi import APIRouter
from fastapi import HTTPException
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
