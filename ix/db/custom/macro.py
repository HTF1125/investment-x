from __future__ import annotations

import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import Offset, MonthEndOffset
from ix.db.custom.oecd import NumOfOECDLeadingPositiveMoM
from ix.db.custom.pmi import NumOfPmiMfgPositiveMoM, NumOfPmiServicesPositiveMoM
from ix.db.custom.fci import financial_conditions_us
from ix.db.custom.liquidity import m2_world_total


def macro_data() -> pd.DataFrame:
    """Macro dashboard indicators combined into a single DataFrame."""
    return MultiSeries(
        **{
            "ACWI YoY": Series("ACWI US EQUITY:PX_LAST", freq="ME")
            .ffill()
            .pct_change(12)
            .mul(100),
            "Russell2000 YoY": Series("RTY INDEX:PX_LAST", freq="ME")
            .ffill()
            .pct_change(12)
            .mul(100),
            "OECD CLI Diffusion Index": NumOfOECDLeadingPositiveMoM(),
            "PMI Manufacturing Diffusion Index": NumOfPmiMfgPositiveMoM(),
            "PMI Services Diffusion Index": NumOfPmiServicesPositiveMoM(),
            "US CPI YoY": Series("USPR1980783:PX_LAST", freq="ME")
            .ffill()
            .pct_change(12)
            .mul(100),
            "Taiwan Exports YoY": Series("TW.FTEXP").pct_change(12) * 100,
            "Singapore Exports YoY": Series("SGFT1039935").pct_change(12) * 100,
            "Korea Exports YoY": Series("KR.FTEXP").pct_change(12) * 100,
            "US PPI YoY": Series("USPR7664543:PX_LAST", freq="ME")
            .ffill()
            .pct_change(12)
            .mul(100),
            "GAP(CPI-PPI)": Series("USPR1980783:PX_LAST", freq="ME")
            .ffill()
            .pct_change(12)
            .mul(100)
            - Series("USPR7664543:PX_LAST", freq="ME").ffill().pct_change(12).mul(100),
            "Staples/S&P500 YoY": Series("XLP US EQUITY:PX_LAST")
            .div(Series("SPY US EQUITY:PX_LAST"))
            .pct_change(250)
            .mul(100),
            "Financial Conditions (US, 26W Lead)": Offset(
                financial_conditions_us().mul(100), days=26
            ),
            "ISM Manufacturing PMI": Series("ISMPMI_M:PX_LAST"),
            "Global M2 YoY (%, 9M Lead)": Offset(
                m2_world_total().pct_change(12), months=9
            )
            * 100,
            "Citi Economic Surprise Index (US)": Series("USFXCESIUSD:PX_LAST"),
            "Dollar deviation from ST Trend (%, 10W Lead)": Offset(
                Series("DXY Index:PX_LAST", freq="W-Fri").rolling(30).mean()
                - Series("DXY Index:PX_LAST", freq="W-Fri"),
                days=70,
            ),
            "UST10Y deviation from Trend (%, 10W Lead)": Offset(
                Series("TRYUS10Y:PX_YTM", freq="W-Fri").rolling(30).mean()
                - Series("TRYUS10Y:PX_YTM", freq="W-Fri"),
                days=70,
            )
            * 100,
            "UST10-3Y Spread (bps)": Series("TRYUS10Y:PX_YTM")
            .sub(Series("TRYUS3Y:PX_LAST"))
            .mul(100),
            "Loans & Leases in Bank Credit YoY": Series(
                "FRBBCABLBA@US:PX_LAST", freq="W-Fri"
            )
            .ffill()
            .pct_change(52)
            .mul(100),
            "SLOOS, C&I Standards Large & Medium Firms (12M Lead)": MonthEndOffset(
                Series("USSU0486263", freq="ME").ffill(), 12
            ),
            "ADP Payroll MoM": Series("USLM0985981").diff(),
            "NonFarm Payroll MoM": Series("BLSCES0000000001:PX_LAST").diff(),
            "NonFarm Payroll (Private) MoM": Series("BLSCES0500000001:PX_LAST").diff(),
            "NFIB Actual 3 Month Earnings Change YoY": Series(
                "USSU0062562:PX_LAST"
            ).diff(12),
        }
    )
