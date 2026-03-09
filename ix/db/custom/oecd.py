from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import MonthEndOffset


OECD_CLI_CODES = [
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

OECD_CLI_EM_CODES = [
    "TUR.LOLITOAA.STSA:PX_LAST",
    "IND.LOLITOAA.STSA:PX_LAST",
    "IDN.LOLITOAA.STSA:PX_LAST",
    "CHN.LOLITOAA.STSA:PX_LAST",
    "KOR.LOLITOAA.STSA:PX_LAST",
    "BRA.LOLITOAA.STSA:PX_LAST",
    "ESP.LOLITOAA.STSA:PX_LAST",
    "ITA.LOLITOAA.STSA:PX_LAST",
    "MEX.LOLITOAA.STSA:PX_LAST",
]

OECD_CLI_DIFFUSION_WORLD_CODES = [
    "USA", "TUR", "IND", "IDN", "CHN", "KOR", "BRA",
    "AUS", "CAN", "DEU", "ESP", "FRA", "GBR", "ITA", "JPN", "MEX",
]
OECD_CLI_DIFFUSION_DEVELOPED_CODES = [
    "USA", "AUS", "CAN", "DEU", "FRA", "GBR", "ITA", "JPN",
]
OECD_CLI_DIFFUSION_EMERGING_CODES = [
    "TUR", "IND", "IDN", "CHN", "KOR", "BRA", "ESP", "MEX",
]


def _positive_mom_pct(codes: list[str]) -> pd.Series:
    data = pd.DataFrame({code: Series(code) for code in codes}).ffill().diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    return percent_positive.sort_index()


def NumOfOECDLeadingPositiveMoM() -> pd.Series:
    """Percentage of OECD CLI series with positive MoM changes."""
    return _positive_mom_pct(OECD_CLI_CODES)


def NumOfOecdCliMoMPositiveEM() -> pd.Series:
    """Percentage of OECD CLI EM series with positive MoM changes."""
    return _positive_mom_pct(OECD_CLI_EM_CODES)


def oecd_cli_regime() -> pd.DataFrame:
    """OECD CLI regime percentages."""
    from ix.core.technical.regime import Regime1
    from ix.core.technical.moving_average import MACD

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in OECD_CLI_CODES}
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


def _oecd_cli_diffusion(codes: list[str], lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """Compute OECD CLI diffusion index for given country codes."""
    series_dict = {
        c: Series(f"{c}.LOLITOAA.STSA:PX_LAST", freq="ME")
        for c in codes
    }
    cli_data = MultiSeries(**series_dict)
    cli_diff = cli_data.diff().dropna(how="all")
    pos_count = (cli_diff > 0).sum(axis=1)
    valid_count = cli_diff.notna().sum(axis=1)
    raw = (pos_count / valid_count).replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0) * 100

    diffusion = MonthEndOffset(
        raw.to_frame(), lead_months
    ).iloc[:, 0].resample(freq).ffill()
    return diffusion


def oecd_cli_diffusion_world(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — World."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_WORLD_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (World)"
    return s


def oecd_cli_diffusion_developed(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — Developed Markets."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_DEVELOPED_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (DM)"
    return s


def oecd_cli_diffusion_emerging(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — Emerging Markets."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_EMERGING_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (EM)"
    return s


# Backward-compatible wrapper
class OecdCliDiffusionIndex:
    def __init__(self, lead_months: int = 3, freq: str = "W-FRI") -> None:
        self.lead_months = lead_months
        self.freq = freq

    @property
    def world(self) -> pd.Series:
        return oecd_cli_diffusion_world(self.lead_months, self.freq)

    @property
    def developed(self) -> pd.Series:
        return oecd_cli_diffusion_developed(self.lead_months, self.freq)

    @property
    def emerging(self) -> pd.Series:
        return oecd_cli_diffusion_emerging(self.lead_months, self.freq)
