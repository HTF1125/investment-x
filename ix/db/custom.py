from ix.db.query import Series
from ix.core import StandardScaler
import pandas as pd


def FinancialConditionsIndexUS() -> pd.Series:
    fci_us = pd.concat(
        [
            StandardScaler(-Series("DXY Index:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScaler(-Series("TRYUS10Y:PX_YTM", freq="W").ffill(), 52 * 3),
            StandardScaler(-Series("TRYUS30Y:PX_YTM", freq="W").ffill(), 52 * 3),
            StandardScaler(Series("SPX Index:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScaler(-Series("MORTGAGE30US:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScaler(-Series("CL1 Comdty:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScaler(-Series("BAMLC0A0CM:PX_LAST", freq="W").ffill(), 52 * 3),
        ],
        axis=1,
    )
    fci_us.index = pd.to_datetime(fci_us.index)
    fci_us = fci_us.sort_index()
    fci_us = fci_us.mean(axis=1).ewm(span=4 * 12).mean()
    fci_us.name = "Financial Conditions US"
    return fci_us


def financial_conditions_index_us() -> pd.Series:
    raw = pd.concat(
        [
            -Series("DXY Index:PX_LAST", freq="W"),
            -Series("TRYUS10Y:PX_YTM", freq="W"),
            -Series("TRYUS30Y:PX_YTM", freq="W"),
            Series("SPX Index:PX_LAST", freq="W"),
            -Series("MORTGAGE30US", freq="W"),
            -Series("CL1 Comdty:PX_LAST", freq="W"),
            -Series("BAMLC0A0CM", freq="W"),
        ],
        axis=1,
    ).ffill()
    normalized = raw.apply(StandardScaler, axis="index", window=52 * 3)
    mean = {i: row.mean() for i, row in normalized.iterrows()}
    financial_conditions = pd.Series(mean)
    financial_conditions = financial_conditions.ewm(
        span=4 * 12,
    ).mean()
    financial_conditions.name = "Financial Conditions US"
    return financial_conditions


from ix.core.tech.regime import Regime1
from ix.core.tech.ma import MACD


def oecd_cli_regime() -> pd.DataFrame:

    indicators = [
        "USA.LOLITOAA.STSA:PX_LAST",
        "TUR.LOLITOAA.STSA:PX_LAST",
        "IND.LOLITOAA.STSA:PX_LAST",
        "IDN.LOLITOAA.STSA:PX_LAST",
        "A5M.LOLITOAA.STSA:PX_LAST",
        "CHN.LOLITOAA.STSA:PX_LAST",
        "KOR.LOLITOAA.STSA:PX_LAST",
        "BRA.LOLITOAA.STSA:PX_LAST",
        "AUS.LOLITOAA.STSA:PX_LAST",
        "CAN.LOLITOAA.STSA:PX_LAST",
        "DEU.LOLITOAA.STSA:PX_LAST",
        "ESP.LOLITOAA.STSA:PX_LAST",
        "FRA.LOLITOAA.STSA:PX_LAST",
        "G4E.LOLITOAA.STSA:PX_LAST",
        "G7M.LOLITOAA.STSA:PX_LAST",
        "GBR.LOLITOAA.STSA:PX_LAST",
        "ITA.LOLITOAA.STSA:PX_LAST",
        "JPN.LOLITOAA.STSA:PX_LAST",
        "MEX.LOLITOAA.STSA:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )
    return regimes


def pmi_manufacturing_regime() -> pd.DataFrame:

    indicators = [
        "NTCPMIMFGSA_WLD:PX_LAST",
        "NTCPMIMFGMESA_US:PX_LAST",
        "ISMPMI_M:PX_LAST",
        "NTCPMIMFGSA_CA:PX_LAST",
        "NTCPMIMFGSA_EUZ:PX_LAST",
        "NTCPMIMFGSA_DE:PX_LAST",
        "NTCPMIMFGSA_FR:PX_LAST",
        "NTCPMIMFGSA_IT:PX_LAST",
        "NTCPMIMFGSA_ES:PX_LAST",
        "NTCPMIMFGSA_GB:PX_LAST",
        "NTCPMIMFGSA_JP:PX_LAST",
        "NTCPMIMFGSA_KR",
        "NTCPMIMFGSA_IN:PX_LAST",
        "NTCPMIMFGNSA_CN:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )
    return regimes


def pmi_services_regime() -> pd.DataFrame:

    indicators = [
        "NTCPMISVCBUSACTSA_WLD:PX_LAST",
        "NTCPMISVCBUSACTMESA_US:PX_LAST",
        "ISMNMI_NM:PX_LAST",
        "NTCPMISVCBUSACTSA_EUZ:PX_LAST",
        "NTCPMISVCBUSACTSA_DE:PX_LAST",
        "NTCPMISVCBUSACTSA_FR:PX_LAST",
        "NTCPMISVCBUSACTSA_IT:PX_LAST",
        "'NTCPMISVCBUSACTSA_ES",
        "NTCPMISVCBUSACTSA_GB:PX_LAST",
        "NTCPMISVCPSISA_AU",
        "NTCPMISVCBUSACTSA_JP:PX_LAST",
        "NTCPMISVCBUSACTSA_CN:PX_LAST",
        "NTCPMISVCBUSACTSA_IN",
        "NTCPMISVCBUSACTSA_BR:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )
    return regimes
