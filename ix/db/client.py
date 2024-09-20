import pandas as pd
from ix.db.models import Timeseries


def get_pxs(
    codes: str | list[str] | set[str] | tuple[str, ...] | dict[str, str] | None = None,
    field: str = "PxLast",
    start: str | None = None,
) -> pd.DataFrame:

    if isinstance(codes, dict):
        # If tickers is a dictionary, get the data for the keys and rename columns
        keys = list(codes.keys())
        data = get_pxs(codes=keys)
        data = data.rename(columns=codes)
        return data

    # If tickers is a string, split it into a list
    if isinstance(codes, str):
        codes = codes.replace(",", " ").split()

    px_data = []

    if codes is None:
        # Fetch all prices if no specific codes are provided
        for price in Timeseries.find_many({"field": field}).run():
            data = pd.Series(price.data)
            data.name = price.code
            px_data.append(data)
    else:
        # Fetch prices for the specified codes
        for code in codes:
            timeseries = Timeseries.find_one({"code": code, "field": field}).run()
            if timeseries is None:
                continue
            data = pd.Series(timeseries.data)
            data.name = code
            px_data.append(data)

    out = pd.concat(px_data, axis=1)
    if start:
        out = out.loc[start:]
    return out
