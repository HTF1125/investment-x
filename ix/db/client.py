import pandas as pd
from ix import db


def get_pxs(
    codes: str | list[str] | set[str] | tuple[str, ...] | dict[str, str] | None = None,
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
        for pxlast in db.PxLast.find_all().run():
            pxlast = pd.Series(data=pxlast.data, name=pxlast.code)
            px_data.append(pxlast)
    else:
        # Fetch prices for the specified codes
        for code in codes:
            pxlast = db.PxLast.find_one({"code": code}).run()
            if pxlast is None:
                continue
            px_last = pd.Series(data=pxlast.data, name=pxlast.code)
            px_data.append(px_last)

    out = pd.concat(px_data, axis=1)
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    if start:
        out = out.loc[start:]
    return out
