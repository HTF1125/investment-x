import pandas as pd
from ix.db.models import Ticker


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
        for ticker in Ticker.find_all().run():
            px_last = pd.Series(data=ticker.px_last, name=ticker.code)
            px_data.append(px_last)
    else:
        # Fetch prices for the specified codes
        for code in codes:
            ticker = Ticker.find_one({"code": code}).run()
            if ticker is None:
                continue
            px_last = pd.Series(data=ticker.px_last, name=ticker.code)
            px_data.append(px_last)

    out = pd.concat(px_data, axis=1)
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    if start:
        out = out.loc[start:]
    return out
