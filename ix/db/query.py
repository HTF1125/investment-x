from typing import Optional, Union
import numpy as np
import pandas as pd

from scipy.optimize import curve_fit
from pandas.tseries.offsets import MonthEnd
from ix.db.models import Timeseries
from cachetools import TTLCache, cached
from ix import core
from ix.core.stat import Cycle
from ix.misc.date import today

cache = TTLCache(maxsize=128, ttl=600)

# Constants for PMI codes
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


# Helper function to calculate positive MoM percentage
def _calculate_positive_mom_percentage(codes: list[str]) -> pd.Series:
    """Calculate percentage of series with positive month-over-month changes."""
    data = pd.DataFrame({code: Series(code) for code in codes}).ffill().diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    percent_positive = percent_positive.sort_index()
    return percent_positive


# Helper function to calculate regime percentages
def _calculate_regime_percentages(codes: list[str]) -> pd.DataFrame:
    """Calculate regime percentages from a list of series codes."""
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


def Regime1(series: pd.Series) -> pd.Series:
    """Calculate regime classification based on MACD histogram."""
    macd = core.MACD(px=series).histogram
    regime = core.Regime1(series=macd).to_dataframe()["regime"]
    return regime


def MultiSeries(**series: pd.Series) -> pd.DataFrame:
    out = []
    for name, s in series.items():
        s.name = name
        out.append(s)

    data = pd.concat(out, axis=1)
    data.index = pd.to_datetime(data.index)
    data = data.sort_index()
    data.index.name = "Date"
    return data

# @cached(cache)
def Series(
    code: str,
    freq: str | None = None,
    name: str | None = None,
    ccy: str | None = None,
    scale: int | None = None,
) -> pd.Series:
    """
    Return a pandas Series for `code`, resampled to `freq` if provided,
    otherwise to the DB frequency `ts.frequency`. Slice to [ts.start, today()].

    Alias:
      If code contains '=', e.g. 'NAME=REAL_CODE', return REAL_CODE with name 'NAME'.
    """
    try:
        # Alias handling first, only if there isn't a direct match

        if ":" not in code:
            code = f"{code}:PX_LAST"
        code = code.upper()

        # Query using SQLAlchemy
        from ix.db.conn import Session

        with Session() as session:
            ts = session.query(Timeseries).filter(Timeseries.code == code).first()

            if ts is None:
                # Extract code and check for alias pattern after session closes
                ts_code = None
                ts_start = None
                ts_frequency = None
            else:
                # Extract all needed attributes while still in session
                ts_code = ts.code
                ts_start = ts.start
                ts_frequency = ts.frequency
                # Get data while still in session
                s = ts.data.copy()
        # Session is now closed, ts is detached

        if ts is None and "=" in code:
            name, new_code = code.split("=", maxsplit=1)
            s = Series(code=new_code, freq=freq).sort_index()
            s.name = name
            return s

        if ts is None:
            # No series found and not an alias pattern
            return pd.Series(name=code)

        # Ensure DateTimeIndex just in case
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index, errors="coerce")
            s = s.dropna()

        # Compute slice window: [start, today]
        start_dt = pd.to_datetime(ts_start) if ts_start else s.index.min()
        end_dt = pd.to_datetime(today())

        # Choose target frequency: override > DB value
        if freq:
            try:
                # Forward-fill daily series first to ensure target frequency dates get values
                # This ensures month-end dates (e.g., 2025-10-31) get the value from the last
                # available day in the month (e.g., 2025-10-30)
                s = s.resample("D").last().ffill()
                idx = pd.date_range(start_dt, end_dt, freq=freq)
                # Resample to target frequency using last observation in each bin
                s = s.reindex(idx)
            except Exception:
                # If target_freq is invalid, fall back to unsampled series
                pass

        # Slice to [start, today] regardless of resampling for consistency
        s = s.loc[start_dt:end_dt]

        # Currency conversion to requested `ccy`
        src_ccy = (ts.currency or "").upper() if hasattr(ts, "currency") else ""
        tgt_ccy = (ccy or "").upper() if ccy else ""

        def _fx_pair_series(base: str, quote: str) -> pd.Series:
            """Fetch FX rate series base/quote as PX_LAST, daily and ffilled.
            Tries both 'Curncy' and 'CURNCY' tickers.
            Returns empty series when not found.
            """
            if not base or not quote or base == quote:
                return pd.Series(dtype=float)
            for asset_class in ("Curncy", "CURNCY"):
                fx_code = f"{base}{quote} {asset_class}:PX_LAST"
                fx = Series(fx_code, freq="D")
                if not fx.empty:
                    return fx.ffill()
            return pd.Series(dtype=float)

        if tgt_ccy and src_ccy and src_ccy != tgt_ccy:
            # Try direct pair
            fx = _fx_pair_series(src_ccy, tgt_ccy)
            if not fx.empty:
                fx = fx.reindex(s.index).ffill()
                s = s.mul(fx).dropna()
            else:
                # Try reverse pair
                fx_rev = _fx_pair_series(tgt_ccy, src_ccy)
                if not fx_rev.empty:
                    fx_rev = fx_rev.reindex(s.index).ffill()
                    s = s.div(fx_rev).dropna()
                else:
                    # Fallback via USD cross (src -> USD -> tgt)
                    pivot = "USD"
                    tmp = s
                    if src_ccy != pivot:
                        fx1 = _fx_pair_series(src_ccy, pivot)
                        if fx1.empty:
                            fx1 = _fx_pair_series(pivot, src_ccy)
                            if not fx1.empty:
                                fx1 = fx1.reindex(tmp.index).ffill()
                                tmp = tmp.div(fx1)
                        else:
                            fx1 = fx1.reindex(tmp.index).ffill()
                            tmp = tmp.mul(fx1)
                    if tgt_ccy != pivot:
                        fx2 = _fx_pair_series(pivot, tgt_ccy)
                        if fx2.empty:
                            fx2 = _fx_pair_series(tgt_ccy, pivot)
                            if not fx2.empty:
                                fx2 = fx2.reindex(tmp.index).ffill()
                                tmp = tmp.div(fx2)
                        else:
                            fx2 = fx2.reindex(tmp.index).ffill()
                            tmp = tmp.mul(fx2)
                    s = tmp.dropna()

        # Apply scale conversion if requested:
        # Convert stored series by its intrinsic ts.scale to target `scale`.
        if scale is not None:
            try:
                ts_scale = int(ts.scale or 1)
            except Exception:
                ts_scale = 1
            try:
                target_scale = int(scale) if scale else None
            except Exception:
                target_scale = None
            if target_scale and target_scale != 0:
                s = s.mul(ts_scale).div(target_scale)

        # Override name if provided
        if name:
            s.name = name

        return s
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading series {code}: {e}")
        return pd.Series(name=code, dtype=float)


def Resample(
    series: pd.Series,
    freq: str = "ME",
) -> pd.Series:
    """Resample series to target frequency using last value."""
    return series.resample(freq).last()


def PctChange(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    """Calculate percentage change over specified periods."""
    return series.pct_change(periods=periods).dropna()


def Diff(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    """Calculate difference over specified periods."""
    return series.diff(periods=periods)


def MovingAverage(
    series: pd.Series,
    window: int = 3,
) -> pd.Series:
    """Calculate moving average over specified window."""
    return series.rolling(window=window).mean()


def MonthEndOffset(
    series: pd.Series,
    months: int = 3,
) -> pd.Series:
    """Offset series index by months and align to month end."""
    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted + MonthEnd(0)
    return series


def MonthsOffset(
    series: pd.Series,
    months: int,
) -> pd.Series:
    """Offset series index by specified number of months."""
    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted
    return series


def Offset(
    series: pd.Series,
    months: int = 0,
    days: int = 0,
) -> pd.Series:
    """Offset series index by specified months and/or days."""
    shifted = series.index + pd.DateOffset(months=months, days=days)
    series.index = shifted
    return series


def StandardScalar(
    series: pd.Series,
    window: int = 20,
) -> pd.Series:
    """Standardize series using rolling mean and standard deviation."""
    roll = series.rolling(window=window)
    mean, std = roll.mean(), roll.std()
    return series.sub(mean).div(std).dropna()


def Clip(
    series: pd.Series,
    lower: Optional[float] = None,
    upper: Optional[float] = None,
) -> pd.Series:
    """Clip series values to specified lower and upper bounds."""
    return series.clip(lower=lower, upper=upper)


def Ffill(series: pd.Series) -> pd.Series:
    """Forward fill missing values in a series."""
    return series.ffill()

    """
    series: pd.Series, 결측치 자동 제거
    max_points_per_cycle: int, 한 사이클당 최대 포인트 수. None 이면 제약 없음.
    """

    # 1) Prepare t and y
    series_clean = series.dropna()
    t = np.arange(len(series_clean))
    y = series_clean.values.astype(float)

    # 2) Initial amplitude & offset
    A0 = (y.max() - y.min()) / 2
    C0 = y.mean()

    # 3) FFT-based frequency & phase guesses
    yf = np.fft.fft(y - C0)
    xf = np.fft.fftfreq(len(t), d=1)
    peak_idx = np.argmax(np.abs(yf[1 : len(y) // 2])) + 1
    f0 = abs(xf[peak_idx])
    phi0 = 0.0

    # 4) Sine model
    def sine_model(t, A, f, phi, C):
        return A * np.sin(2 * np.pi * f * t + phi) + C

    # 5) Setup bounds and initial guess
    use_bounds = False
    if max_points_per_cycle:
        f_min = 1.0 / max_points_per_cycle
        f_max = 0.5  # Nyquist limit
        bounds = ([0.0, f_min, -np.pi, -np.inf], [np.inf, f_max, np.pi, np.inf])
        # initial f0 must lie strictly inside (f_min, f_max)
        f0 = np.clip(f0, f_min + 1e-6, f_max - 1e-6)
        use_bounds = True

    p0 = [A0, f0, phi0, C0]

    # 6) Curve fitting
    if use_bounds:
        popt, pcov = curve_fit(sine_model, t, y, p0=p0, bounds=bounds)
    else:
        popt, pcov = curve_fit(sine_model, t, y, p0=p0)

    A_fit, f_fit, phi_fit, C_fit = popt

    # 7) Negative amplitude이면 위상 반전
    if A_fit < 0:
        phi_fit += np.pi

    # 8) 10/90 백분위수 계산
    p10, p90 = np.percentile(y, 10), np.percentile(y, 90)

    # 9) 스케일된 사인곡선 생성
    A_scaled = (p90 - p10) / 2
    C_scaled = (p90 + p10) / 2
    scaled = pd.Series(
        sine_model(t, A_scaled, f_fit, phi_fit, C_scaled), index=series_clean.index
    )

    return scaled


def find_best_window(series: pd.Series, max_lag: Optional[int] = None) -> int:
    """
    Automatically find the dominant cycle length (best window size)
    using the autocorrelation function.
    """
    if max_lag is None:
        max_lag = min(365, len(series) // 2)  # sensible default for daily data
    ac = [series.autocorr(lag) for lag in range(1, max_lag)]
    best_window = np.argmax(ac) + 1  # +1 because lags start at 1
    return best_window


def CycleForecast(
    series: pd.Series, forecast_steps: int = 12, window_size: Optional[int] = None
) -> pd.Series:

    series = series.dropna()
    t = np.arange(len(series))
    y = series.values
    y_centered = y - y.mean()

    # --- Automatically determine best window size if not provided ---
    if window_size is None:
        window_size = find_best_window(series)
        # Ensure window_size is not too small
        window_size = max(window_size, 8)
        # If series is very short, adjust window_size
        window_size = min(window_size, len(series) // 2)

    # --- Estimate local dominant frequency using a sliding window ---
    freqs = []
    for i in range(0, len(y) - window_size + 1, max(1, window_size // 2)):
        window = y_centered[i : i + window_size]
        yf = np.fft.fft(window)
        xf = np.fft.fftfreq(window_size)
        idx_peak = np.argmax(np.abs(yf[1 : window_size // 2])) + 1
        freqs.append(abs(xf[idx_peak]))
    # Interpolate frequencies to the full length
    freq_trend = np.interp(t, np.linspace(0, len(t) - 1, len(freqs)), freqs)

    # --- Define a model with time-varying frequency ---
    def sine_model_varfreq(t, A, phi, C):
        phase = 2 * np.pi * np.cumsum(freq_trend)
        return A * np.sin(phase + phi) + C

    # --- Fit the model ---
    popt, _ = curve_fit(
        sine_model_varfreq,
        t,
        y,
        p0=[(y.max() - y.min()) / 2, 0, y.mean()],
        maxfev=10000,
    )

    # --- Project forward ---
    t_forecast = np.arange(len(t) + forecast_steps)
    freq_forecast = np.concatenate(
        [freq_trend, np.full(forecast_steps, freq_trend[-1])]
    )
    phase_forecast = 2 * np.pi * np.cumsum(freq_forecast)
    y_fitted = popt[0] * np.sin(phase_forecast + popt[1]) + popt[2]

    # --- Construct result ---
    full_index = pd.date_range(
        series.index[0], periods=len(t_forecast), freq=pd.infer_freq(series.index)
    )
    fitted_series = pd.Series(y_fitted, index=full_index)

    return fitted_series


def Drawdown(series: pd.Series, window: Optional[int] = None) -> pd.Series:
    """Calculate drawdown from peak (rolling or expanding)."""
    if window:
        return series.div(series.rolling(window=window).max()).abs()
    return series.div(series.expanding().max()).abs()


def Rebase(series: pd.Series) -> pd.Series:
    """Rebase series to start at 1.0 using first non-null value."""
    return series / series.dropna().iloc[0]


def PMI_Manufacturing_Regime() -> pd.DataFrame:
    """Calculate PMI Manufacturing regime percentages."""
    return _calculate_regime_percentages(PMI_MANUFACTURING_CODES)


def PMI_Services_Regime() -> pd.DataFrame:
    """Calculate PMI Services regime percentages."""
    result = _calculate_regime_percentages(PMI_SERVICES_CODES)
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    return result


def FinancialConditionsIndex1() -> pd.Series:
    """Calculate Financial Conditions Index from multiple standardized series."""
    series = [
        StandardScalar(Series("VIX Index:PX_LAST"), 160),
        StandardScalar(Series("MOVE Index:PX_LAST"), 160),
        StandardScalar(Series("BAMLH0A0HYM2"), 160),
        StandardScalar(Series("BAMLC0A0CM"), 160),
    ]
    result = pd.concat(series, axis=1).ffill().mean(axis=1)
    return result


def FedNetLiquidity() -> pd.Series:
    """Calculate Fed Net Liquidity (Assets - Treasury - Repo) in trillions USD."""
    # 1) Load raw series
    asset_mil = Series("WALCL")  # millions USD
    treasury_bil = Series("WTREGEN")  # billions USD
    repo_bil = Series("RRPONTSYD")  # billions USD

    # 2) Normalize to trillions USD
    asset = asset_mil.div(1_000_000)  # → trillions
    treasury = treasury_bil.div(1_000_000)  # → trillions
    repo = repo_bil.div(1_000)  # → trillions
    # 3) Combine
    df = pd.concat({"asset": asset, "treasury": treasury, "repo": repo}, axis=1)
    # 4) Weekly on Wednesday, take last value & forward-fill
    weekly = df.resample("W-WED").last().ffill()
    # 5) Compute net liquidity
    weekly["net_liquidity_T"] = weekly["asset"] - weekly["treasury"] - weekly["repo"]
    daily = weekly["net_liquidity_T"].resample("B").ffill()
    return daily.dropna()


def NumOfPmiServicesPositiveMoM() -> pd.Series:
    """Calculate percentage of PMI Services series with positive MoM changes."""
    return _calculate_positive_mom_percentage(PMI_SERVICES_CODES)


def oecd_cli_regime() -> pd.DataFrame:
    """Calculate OECD CLI regime percentages."""
    return _calculate_regime_percentages(OECD_CLI_CODES)


def CustomSeries(code: str) -> Union[pd.Series, pd.DataFrame, None]:
    """
    Return custom calculated series based on code.

    Returns:
        pd.Series or pd.DataFrame depending on the code requested.
        Returns None if code is not recognized.
    """
    if code == "GlobalGrowthRegime-Expansion":
        return PMI_Manufacturing_Regime()["Expansion"]

    if code == "GlobalGrowthRegime-Slowdown":
        return PMI_Manufacturing_Regime()["Slowdown"]

    if code == "GlobalGrowthRegime-Contraction":
        return PMI_Manufacturing_Regime()["Contraction"]

    if code == "GlobalGrowthRegime-Recovery":
        return PMI_Manufacturing_Regime()["Recovery"]

    if code == "NumOfOECDLeadingPositiveMoM":
        return _calculate_positive_mom_percentage(OECD_CLI_CODES)

    if code == "NumOfPmiPositiveMoM":
        return _calculate_positive_mom_percentage(PMI_MANUFACTURING_CODES)

    if code == "GlobalM2":
        data = pd.concat(
            [
                Series("US.MAM2").dropna() / 1000,
                Series("EUZ.MAM2")
                * Resample(Series("EURUSD Curncy:PX_LAST"), "ME").dropna()
                / 1000
                / 1000,
                Series("GB.MAM2")
                / Resample(Series("USDGBP Curncy:PX_LAST"), "ME").dropna()
                / 1000
                / 1000,
                Series("JP.MAM2")
                / Resample(Series("USDJPY Curncy:PX_LAST"), "ME").dropna()
                / 10
                / 1000,
                Series("CN.MAM2")
                / Resample(Series("USDCNY Curncy:PX_LAST"), "ME").dropna()
                / 10
                / 1000,
            ],
            axis=1,
        ).dropna()
        data = data.sum(axis=1).dropna()
        return data

    if code == "LocalIndices2":
        from ix.db import get_timeseries

        # 1) 벤치마크 티커 정의
        codes = {
            "SP500": "SPX Index:PX_LAST",
            "DJIA30": "INDU Index:PX_LAST",
            "NASDAQ": "CCMP Index:PX_LAST",
            "Russell2": "RTY Index:PX_LAST",
            "Stoxx50": "SX5E Index:PX_LAST",
            "FTSE100": "UKX Index:PX_LAST",
            "DAX": "DAX Index:PX_LAST",
            "CAC": "CAC Index:PX_LAST",
            "Nikkei225": "NKY Index:PX_LAST",
            "TOPIX": "TPX Index:PX_LAST",
            "KOSPI": "KOSPI Index:PX_LAST",
            "NIFTY": "NIFTY Index:PX_LAST",
            "HangSeng": "HSI Index:PX_LAST",
            "SSE": "SHCOMP Index:PX_LAST",
        }

        # 2) 시계열 불러와서 일별로 리샘플 → 결측일 전일치 보간
        series_list = []
        for name, ticker in codes.items():
            ts = get_timeseries(ticker).data
            ts.name = name
            series_list.append(ts)

        datas = pd.concat(series_list, axis=1)
        datas = datas.resample("D").last().ffill()

        # 3) 오늘 날짜와 기준일 정의
        today = datas.index[-1]
        start_year = pd.Timestamp(year=today.year, month=1, day=1)
        one_month = today - pd.DateOffset(months=1)
        three_mo = today - pd.DateOffset(months=3)
        one_year = today - pd.DateOffset(years=1)

        # 4) 기준 시세(asof)로부터 퍼센트 변동 계산 함수
        def pct_from(base_date):
            base = datas.asof(base_date)
            return (datas.iloc[-1] / base - 1).round(4) * 100

        # 5) 각 기간별 결과 조합
        output = []

        level = datas.iloc[-1].round(2)
        level.name = "Level"
        output.append(level)
        output.append(pct_from(today - pd.DateOffset(days=1)).rename("1D"))
        output.append(pct_from(today - pd.DateOffset(days=7)).rename("1W"))
        output.append(pct_from(one_month).rename("1M"))
        output.append(pct_from(three_mo).rename("3M"))
        output.append(pct_from(one_year).rename("1Y"))
        output.append(pct_from(start_year).rename("YTD"))

        result = pd.concat(output, axis=1)
        return result

    if code == "FedNetLiquidity":
        return FedNetLiquidity()

    if code == "OecdCliRegime-Expansion":
        return oecd_cli_regime()["Expansion"]

    if code == "OecdCliRegime-Slowdown":
        return oecd_cli_regime()["Slowdown"]

    if code == "OecdCliRegime-Contraction":
        return oecd_cli_regime()["Contraction"]

    if code == "OecdCliRegime-Recovery":
        return oecd_cli_regime()["Recovery"]

    # Return None if code not found (caller should handle)
    return None


def NumOfOecdCliMoMPositiveEM() -> pd.Series:
    """Calculate percentage of OECD CLI EM series with positive MoM changes."""
    return _calculate_positive_mom_percentage(OECD_CLI_EM_CODES)


def financial_conditions_us() -> pd.Series:
    """Calculate US Financial Conditions Index from multiple standardized series."""
    dd = (
        pd.concat(
            [
                StandardScalar(-Series("DXY Index:PX_LAST", freq="W"), 4 * 6),
                StandardScalar(-Series("TRYUS10Y:PX_YTM", freq="W"), 4 * 6),
                StandardScalar(-Series("TRYUS30Y:PX_YTM", freq="W"), 4 * 6),
                StandardScalar(Series("SPX Index:PX_LAST", freq="W"), 4 * 6),
                StandardScalar(-Series("MORTGAGE30US", freq="W"), 4 * 6),
                StandardScalar(-Series("CL1 Comdty:PX_LAST", freq="W"), 4 * 6),
                StandardScalar(-Series("BAMLC0A0CM", freq="W"), 4 * 6),
            ],
            axis=1,
        )
        .mean(axis=1)
        .ewm(span=4 * 12)
        .mean()
    )
    dd.index = pd.to_datetime(dd.index)
    dd = dd.sort_index()

    dd.name = "FCI2"
    return dd


def FinancialConditionsKR() -> pd.Series:
    """Calculate Korea Financial Conditions Index from multiple standardized series."""
    dd = (
        pd.concat(
            [
                StandardScalar(-Series("USDKRW Curncy:PX_LAST", freq="W"), 4 * 6),
                StandardScalar(-Series("TRYKR10Y:PX_YTM", freq="W"), 4 * 6),
                StandardScalar(-Series("TRYKR30Y:PX_YTM", freq="W"), 4 * 6),
                StandardScalar(Series("KOSPI Index:PX_LAST", freq="W"), 4 * 6),
                # StandardScalar(-Series("MORTGAGE30US", freq="W"), 4 * 6),
                # StandardScalar(-Series("CL1 Comdty:PX_LAST", freq="W"), 4 * 6),
                # StandardScalar(-Series("BAMLC0A0CM", freq="W"), 4 * 6),
            ],
            axis=1,
        )
        .mean(axis=1)
        .ewm(span=4 * 12)
        .mean()
    )

    dd.name = "FinancialConditionsKR"
    return dd


def NumOfPmiMfgPositiveMoM() -> pd.Series:
    """Calculate percentage of PMI Manufacturing series with positive MoM changes."""
    data = (
        pd.DataFrame({code: Series(code) for code in PMI_MANUFACTURING_CODES})
        .ffill()
        .diff()
    )
    data = data.dropna(thresh=10)
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    return percent_positive


def USD_Open_Interest() -> pd.Series:
    """Calculate USD open interest (long - short)."""
    data = Series("CFTNCLOI%ALLJUSDNYBTOF_US") - Series("CFTNCSOI%ALLJUSDNYBTOF_US")
    return data


def InvestorPositions() -> pd.DataFrame:
    """Calculate investor positions (long - short) for various assets."""
    data = {
        "S&P500": Series("CFTNCLOI%ALLS5C3512CMEOF_US")
        - Series("CFTNCSOI%ALLS5C3512CMEOF_US"),
        "USD": Series("CFTNCLOI%ALLJUSDNYBTOF_US")
        - Series("CFTNCSOI%ALLJUSDNYBTOF_US"),
        "Gold": Series("CFTNCLOI%ALLGOLDCOMOF_US") - Series("CFTNCSOI%ALLGOLDCOMOF_US"),
        "JPY": Series("CFTNCLOI%ALLYENCMEOF_US") - Series("CFTNCSOI%ALLYENCMEOF_US"),
        "UST-10Y": Series("CFTNCLOI%ALLTN10YCBOTOF_US")
        - Series("CFTNCSOI%ALLTN10YCBOTOF_US"),
        "UST-Ultra": Series("CFTNCLOI%ALLLUT3163CBOTOF_US")
        - Series("CFTNCSOI%ALLLUT3163CBOTOF_US"),
        "Commodities": Series("CFTNCLOI%ALLDJUBSERCBOTOF_US")
        - Series("CFTNCSOI%ALLDJUBSERCBOTOF_US"),
    }
    data = pd.DataFrame(data)
    return data


def InvestorPositionsvsTrend(weeks: int = 52) -> pd.DataFrame:
    """Calculate investor positions vs rolling trend."""
    data = {
        "S&P500": Series("CFTNCLOI%ALLS5C3512CMEOF_US")
        - Series("CFTNCSOI%ALLS5C3512CMEOF_US"),
        "USD": Series("CFTNCLOI%ALLJUSDNYBTOF_US")
        - Series("CFTNCSOI%ALLJUSDNYBTOF_US"),
        "Gold": Series("CFTNCLOI%ALLGOLDCOMOF_US") - Series("CFTNCSOI%ALLGOLDCOMOF_US"),
        "JPY": Series("CFTNCLOI%ALLYENCMEOF_US") - Series("CFTNCSOI%ALLYENCMEOF_US"),
        "UST-10Y": Series("CFTNCLOI%ALLTN10YCBOTOF_US")
        - Series("CFTNCSOI%ALLTN10YCBOTOF_US"),
        "UST-Ultra": Series("CFTNCLOI%ALLLUT3163CBOTOF_US")
        - Series("CFTNCSOI%ALLLUT3163CBOTOF_US"),
        "Commodities": Series("CFTNCLOI%ALLDJUBSERCBOTOF_US")
        - Series("CFTNCSOI%ALLDJUBSERCBOTOF_US"),
    }
    data = pd.DataFrame(data)
    return data - data.rolling(weeks).mean()


class CalendarYearSeasonality:
    """
    Analyze seasonality of a daily time series by calendar day (month, day), across years.
    Provides original and rebased returns, as well as summary statistics.
    """

    def __init__(self, series: pd.Series):
        """
        Parameters:
        ----------
        series : pd.Series
            Daily or higher-frequency time series with a DateTimeIndex.
        """
        if not isinstance(series.index, pd.DatetimeIndex):
            raise ValueError("Input series must have a DateTimeIndex.")
        self.series = series.resample("D").last().ffill()
        self.series.index = pd.to_datetime(self.series.index)

    def _prepare_pivot(self, exclude_years=None, rebase=False) -> pd.DataFrame:
        """
        Internal helper to pivot the series to (month, day) index and year columns.

        Parameters:
        ----------
        exclude_years : list[int], optional
            Years to exclude from analysis.
        rebase : bool
            If True, rebase each year's values to the first value (as relative return).

        Returns:
        -------
        pivot : pd.DataFrame
            Pivoted DataFrame with (month, day) index and years as columns.
        """
        df = self.series.dropna().to_frame(name="value")
        df["year"] = df.index.year
        df["month"] = df.index.month
        df["day"] = df.index.day
        df = df[~((df["month"] == 2) & (df["day"] == 29))]
        pivot = df.pivot_table(index=["month", "day"], columns="year", values="value")

        if exclude_years:
            pivot = pivot.drop(columns=exclude_years, errors="ignore")

        if rebase:
            pivot = pivot.div(pivot.iloc[0]).sub(1)

        return pivot

    def calculate_statistics(self, pivot: pd.DataFrame) -> pd.DataFrame:
        """
        Compute average, median, and ±1 standard deviation bands.

        Parameters:
        ----------
        pivot : pd.DataFrame
            Pivoted series from _prepare_pivot.

        Returns:
        -------
        stats_df : pd.DataFrame
            DataFrame with calculated seasonal statistics.
        """
        mean = pivot.mean(axis=1).rename("Average")
        std = pivot.std(axis=1)
        return pd.DataFrame(
            {
                "Average": pivot.mean(axis=1).rename("Average"),
                # "+1STD": (mean + std).rename("+1STD"),
                # "-1STD": (mean - std).rename("-1STD"),
            }
        )

    def seasonality(self, exclude_years=None, include_stats=True) -> pd.DataFrame:
        """
        Returns the original unrebased seasonality view.

        Parameters:
        ----------
        exclude_years : list[int], optional
            Years to exclude from analysis.
        include_stats : bool
            If True, include average, median, ±1STD.

        Returns:
        -------
        pd.DataFrame
        """
        pivot = self._prepare_pivot(exclude_years=exclude_years, rebase=False)
        latest_year = pivot.columns.max()
        current_year_series = pivot[latest_year].rename(str(latest_year))
        components = [current_year_series]
        stats = self.calculate_statistics(pivot)
        components = [stats, current_year_series]
        return pd.concat(components, axis=1)

    def rebased(self, exclude_years=None) -> pd.DataFrame:
        """
        Returns the rebased seasonality (e.g., relative returns starting from 0).

        Parameters:
        ----------
        exclude_years : list[int], optional
            Years to exclude from analysis.
        include_stats : bool
            If True, include average, median, ±1STD.

        Returns:
        -------
        pd.DataFrame
        """
        pivot = self._prepare_pivot(exclude_years=exclude_years, rebase=True)
        latest_year = pivot.columns.max()
        current_year_series = pivot[latest_year].rename(str(latest_year))
        components = [current_year_series]
        stats = self.calculate_statistics(pivot)
        components = [stats, current_year_series]
        return pd.concat(components, axis=1)


def NumOfOECDLeadingPositiveMoM() -> pd.Series:
    """Calculate percentage of OECD CLI series with positive MoM changes."""
    return _calculate_positive_mom_percentage(OECD_CLI_CODES)


class M2:

    def __init__(self, freq: str = "ME", currency: str = "USD") -> None:
        self.freq = freq

    @property
    def US(self) -> pd.Series:
        series = Series("US.MAM2", freq=self.freq) / 1000
        series.name = "US"
        return series

    @property
    def EU(self) -> pd.Series:
        fx = Series("EURUSD Curncy:PX_LAST", freq=self.freq)
        series = Series("EUZ.MAM2", freq=self.freq).mul(fx).div(1000_000)
        series.name = "EU"
        return series

    @property
    def UK(self) -> pd.Series:
        fx = Series("USDGBP Curncy:PX_LAST", freq=self.freq)
        series = Series("GB.MAM2", freq=self.freq).div(1000_000).div(fx)
        series.name = "UK"
        return series

    @property
    def CN(self) -> pd.Series:
        fx = Series("USDCNY Curncy:PX_LAST", freq=self.freq)
        series = Series("CN.MAM2", freq=self.freq).div(10_000).div(fx)
        series.name = "CN"
        return series.dropna()

    @property
    def JP(self) -> pd.Series:
        fx = Series("USDJPY Curncy:PX_LAST", freq=self.freq)
        series = Series("JP.MAM2", freq=self.freq).div(10_000).div(fx)
        series.name = "JP"
        return series.dropna()

    @property
    def KR(self) -> pd.Series:
        fx = Series("USDKRW Curncy:PX_LAST", freq=self.freq)
        series = Series("KR.MAM2", freq=self.freq).div(1_000).div(fx)
        series.name = "KR"
        return series.dropna()

    @property
    def CH(self) -> pd.Series:
        fx = Series("USDCHF Curncy:PX_LAST", freq=self.freq)
        series = Series("CH.MAM2", freq=self.freq).div(1_000_000).div(fx)
        series.name = "CH"
        return series.dropna()

    @property
    def CA(self) -> pd.Series:
        fx = Series("USDCAD Curncy:PX_LAST", freq=self.freq).ffill()
        series = Series("CA.MAM2", freq=self.freq).div(1_000_000).div(fx)
        series.name = "CA"
        return series.dropna()

    @property
    def World(self) -> pd.DataFrame:
        data = pd.concat(
            [
                self.US,
                self.UK,
                self.EU,
                self.CN,
                self.JP,
                self.KR,
                self.CA,
                self.CH,
            ],
            axis=1,
        ).ffill()
        return data.dropna()

    @property
    def WorldTotal(self) -> pd.Series:
        series = self.World.sum(axis=1).ffill()
        return series

    @property
    def WorldContribution(self) -> pd.DataFrame:
        if self.freq == "ME":
            period = 12
        elif self.freq.startswith("W"):
            period = 52

        return (
            self.World.diff(period)
            .dropna()
            .div(self.WorldTotal.shift(period), axis=0)
            .dropna()
        )


def LocalIndices() -> pd.DataFrame:
    """Calculate local indices performance metrics (Level, 1D, 1W, 1M, 3M, 1Y, YTD)."""
    from ix.db import get_timeseries

    # 1) 벤치마크 티커 정의
    codes = {
        "SP500": "SPX Index:PX_LAST",
        "DJIA30": "INDU Index:PX_LAST",
        "NASDAQ": "CCMP Index:PX_LAST",
        "Russell2": "RTY Index:PX_LAST",
        "Stoxx50": "SX5E Index:PX_LAST",
        "FTSE100": "UKX Index:PX_LAST",
        "DAX": "DAX Index:PX_LAST",
        "CAC": "CAC Index:PX_LAST",
        "Nikkei225": "NKY Index:PX_LAST",
        "TOPIX": "TPX Index:PX_LAST",
        "KOSPI": "KOSPI Index:PX_LAST",
        "NIFTY": "NIFTY Index:PX_LAST",
        "HangSeng": "HSI Index:PX_LAST",
        "SSE": "SHCOMP Index:PX_LAST",
    }

    # 2) 시계열 불러와서 일별로 리샘플 → 결측일 전일치 보간
    series_list = []
    for name, ticker in codes.items():
        ts = get_timeseries(ticker).data
        ts.name = name
        series_list.append(ts)

    datas = pd.concat(series_list, axis=1)
    datas = datas.resample("D").last().ffill()

    # 3) 오늘 날짜와 기준일 정의
    today = datas.index[-1]
    start_year = pd.Timestamp(year=today.year, month=1, day=1)
    one_month = today - pd.DateOffset(months=1)
    three_mo = today - pd.DateOffset(months=3)
    one_year = today - pd.DateOffset(years=1)

    # 4) 기준 시세(asof)로부터 퍼센트 변동 계산 함수
    def pct_from(base_date):
        base = datas.asof(base_date)
        return (datas.iloc[-1] / base - 1).round(4) * 100

    # 5) 각 기간별 결과 조합
    output = []

    level = datas.iloc[-1].round(2)
    level.name = "Level"
    output.append(level)
    output.append(pct_from(today - pd.DateOffset(days=1)).rename("1D"))
    output.append(pct_from(today - pd.DateOffset(days=7)).rename("1W"))
    output.append(pct_from(one_month).rename("1M"))
    output.append(pct_from(three_mo).rename("3M"))
    output.append(pct_from(one_year).rename("1Y"))
    output.append(pct_from(start_year).rename("YTD"))

    result = pd.concat(output, axis=1)
    return result


class AiCapex:

    def FE_CAPEX_NTMA(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_NTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_LTMA(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_LTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_Q(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_Q",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_QOQ(self) -> pd.DataFrame:
        return (
            self.FE_CAPEX_Q().dropna().resample("W-Fri").last().pct_change(52).mul(100)
        )

    def TOTAL_FE_CAPEX_QOQ(self) -> pd.DataFrame:
        return (
            self.FE_CAPEX_Q()
            .sum(axis=1)
            .dropna()
            .resample("W-Fri")
            .last()
            .pct_change(52)
            .mul(100)
        )

    def TOTAL_FE_CAPEX_YOY(self) -> pd.DataFrame:
        ntma = self.FE_CAPEX_NTMA().sum(axis=1).dropna().resample("W-Fri").last()
        ltma = self.FE_CAPEX_LTMA().sum(axis=1).dropna().resample("W-Fri").last()
        data = (ntma / ltma - 1).mul(100)
        data.name = "YoY"
        return data


def macro_data() -> pd.DataFrame:
    """Calculate macro data indicators and combine into a DataFrame."""
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
                M2("ME").WorldTotal.pct_change(12), months=9
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


def NumPositivePercentByRow(df: pd.DataFrame):
    """Return a Series giving the percentage of positive entries per row (ignoring NaN)."""
    positive = (df > 0).sum(axis=1)
    total = df.notna().sum(axis=1)
    return (positive / total * 100).fillna(0)


def GetChart(name: str):
    """
    Get a chart by name from the database.

    Args:
        name: Chart name (e.g., "AsianExportsYoY")

    Returns:
        Chart object, or None if not found
    """
    from ix.db.conn import Session
    from ix.db.models import Chart

    # Normalize name - remove () if present
    if name.endswith("()"):
        name = name[:-2]

    with Session() as session:
        chart = session.query(Chart).filter(Chart.code == name).first()
        if chart is None:
            return None
        return chart
