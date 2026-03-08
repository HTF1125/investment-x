from __future__ import annotations

import pandas as pd

from ix.db.query import Series


PMI_MANUFACTURING_CODES = [
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

PMI_SERVICES_CODES = [
    "NTCPMISVCBUSACTSA_WLD:PX_LAST",
    "NTCPMISVCBUSACTMESA_US:PX_LAST",
    "ISMNMI_NM:PX_LAST",
    "NTCPMISVCBUSACTSA_EUZ:PX_LAST",
    "NTCPMISVCBUSACTSA_DE:PX_LAST",
    "NTCPMISVCBUSACTSA_FR:PX_LAST",
    "NTCPMISVCBUSACTSA_IT:PX_LAST",
    "NTCPMISVCBUSACTSA_ES:PX_LAST",
    "NTCPMISVCBUSACTSA_GB:PX_LAST",
    "NTCPMISVCPSISA_AU:PX_LAST",
    "NTCPMISVCBUSACTSA_JP:PX_LAST",
    "NTCPMISVCBUSACTSA_CN:PX_LAST",
    "NTCPMISVCBUSACTSA_IN:PX_LAST",
    "NTCPMISVCBUSACTSA_BR:PX_LAST",
]


def _positive_mom_pct(codes: list[str]) -> pd.Series:
    data = pd.DataFrame({code: Series(code) for code in codes}).ffill().diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    return percent_positive.sort_index()


def _regime_percentages(codes: list[str]) -> pd.DataFrame:
    from ix import core

    regimes = []
    for code in codes:
        regime = core.Regime1(core.MACD(Series(code)).histogram).regime
        regimes.append(regime)

    regimes_df = pd.concat(regimes, axis=1)
    regime_counts = regimes_df.apply(
        lambda row: row.value_counts(normalize=True) * 100, axis=1
    )
    regime_pct = regime_counts.fillna(0).round(2)
    return regime_pct[["Expansion", "Slowdown", "Contraction", "Recovery"]].dropna()


def pmi_manufacturing_diffusion() -> pd.Series:
    """% of PMI Mfg series with positive MoM changes."""
    data = (
        pd.DataFrame({code: Series(code) for code in PMI_MANUFACTURING_CODES})
        .ffill()
        .diff()
    )
    data = data.dropna(thresh=10)
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    return (positive_counts / valid_counts) * 100


def pmi_services_diffusion() -> pd.Series:
    """% of PMI Services series with positive MoM changes."""
    return _positive_mom_pct(PMI_SERVICES_CODES)


def pmi_manufacturing_regime() -> pd.DataFrame:
    """PMI Manufacturing regime percentages."""
    return _regime_percentages(PMI_MANUFACTURING_CODES)


def pmi_services_regime() -> pd.DataFrame:
    """PMI Services regime percentages."""
    result = _regime_percentages(PMI_SERVICES_CODES)
    result.index = pd.to_datetime(result.index)
    return result.sort_index()


# Backward-compatible aliases
def NumOfPmiMfgPositiveMoM() -> pd.Series:
    return pmi_manufacturing_diffusion()


def NumOfPmiServicesPositiveMoM() -> pd.Series:
    return pmi_services_diffusion()


def PMI_Manufacturing_Regime() -> pd.DataFrame:
    return pmi_manufacturing_regime()


def PMI_Services_Regime() -> pd.DataFrame:
    return pmi_services_regime()
