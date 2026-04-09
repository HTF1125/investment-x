import pandas as pd


def as_format(item: ..., fmt: str = ".2f") -> str:
    """
    Map a format string over a object.

    Args:
        item (pd.Series, pd.DataFrame, other): item.
        decimals (int, optional): number of decimals. Defaults to 2.

    Returns:
        ...: formatted item
    """
    return format(item, fmt)


def as_date(date: ..., fmt: str = "%Y-%m-%d") -> str:
    """this is a pass through function"""
    return pd.Timestamp(date).strftime(fmt)


def as_percent(item: ..., decimals: int = 2) -> str:
    """this is a pass through function"""
    return as_format(item, f".{decimals}%")


def as_float(item: ..., decimals: int = 2) -> str:
    """this is a pass through function"""
    return as_format(item, f".{decimals}f")
