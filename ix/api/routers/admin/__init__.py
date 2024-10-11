from fastapi import APIRouter
from fastapi import HTTPException
from ix.core.perf import get_period_performances
from ix import db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/tickers")
async def get_tickers() -> list[db.Ticker]:
    tickers = db.Ticker.find_all().run()
    return tickers


@router.get("/ticker/{code}")
async def get_ticker(code: str) -> db.Ticker:
    ticker = db.Ticker.find_one({"code": code}).run()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker not found")
    return ticker


# async Define the POST route to add a new ticker
@router.post("/ticker/add", response_model=db.Ticker)
async def add_ticker(ticker: db.Ticker):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": ticker.code})
    if existing_ticker:
        raise HTTPException(status_code=400, detail="Ticker already exists")
    db.Ticker.insert_one(ticker)
    return ticker


@router.post(
    "/ticker/update",
)
async def mod_ticker(ticker: db.Ticker):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": ticker.code}).run()
    if not existing_ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")

    existing_ticker.set(ticker.model_dump())

    return {"message": "update complete"}


@router.post("/ticker/delete")
async def del_ticker(code: str):
    # Check if the ticker already exists
    existing_ticker = db.Ticker.find_one({"code": code}).run()
    if not existing_ticker:
        raise HTTPException(status_code=400, detail="Ticker not found")
    db.Ticker.delete(existing_ticker)
    return {"message": f"Ticker with code {code} has been deleted successfully"}
