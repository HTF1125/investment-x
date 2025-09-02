from typing import Optional
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from ix.db.models import Timeseries
from cachetools import TTLCache, cached
from ix import core
from ix.misc.date import oneyearbefore, today
# 최대 32개 엔트리, TTL 600초
cacher = TTLCache(maxsize=32, ttl=600)


def Regime1(series) -> pd.Series:
    macd = core.MACD(px=series).histogram
    regime = core.Regime1(series=macd).to_dataframe()["regime"]
    return regime


def MultiSeries(
    *series: str | list[str] | dict | pd.Series,
) -> pd.DataFrame:
    output = []
    for s in series:
        if isinstance(s, str):
            output.append(Series(s))
        elif isinstance(s, list):
            output.append(Series(*s))
        elif isinstance(s, pd.Series):
            output.append(s)
        elif isinstance(s, dict):
            for k, v in s.items():
                s = Series(v)
                s.name = k
                output.append(s)
    output = pd.concat(output, axis=1)
    return output


import pandas as pd
from ix.misc.date import today

def Series(code: str, freq: str | None = None) -> pd.Series:
    """
    Return a pandas Series for `code`, resampled to `freq` if provided,
    otherwise to the DB frequency `ts.frequency`. Slice to [ts.start, today()].

    Alias:
      If code contains '=', e.g. 'NAME=REAL_CODE', return REAL_CODE with name 'NAME'.
    """
    try:
        # Alias handling first, only if there isn't a direct match
        ts = Timeseries.find_one({"code": code}).run()
        if ts is None and "=" in code:
            name, new_code = code.split("=", maxsplit=1)
            s = Series(code=new_code, freq=freq)
            s.name = name
            return s

        if ts is None:
            # No series found and not an alias pattern
            return pd.Series(name=code)

        # Base data (already numeric/cleaned by Timeseries.data)
        s = ts.data.copy()

        # Ensure DateTimeIndex just in case
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index, errors="coerce")
            s = s.dropna()

        # Compute slice window: [start, today]
        start_dt = pd.to_datetime(ts.start) if ts.start else s.index.min()
        end_dt = pd.to_datetime(today())

        # Slice first (in case resample is heavy)
        s = s.reindex(pd.date_range(start_dt, end_dt,freq="D"))
        # Choose target frequency: override > DB value
        target_freq = freq or ts.frequency
        if target_freq:
            try:
                # Resample to last observation in each bin; drop empty bins
                s = s.resample(str(target_freq)).last().dropna()
                # Enforce bounds again post-resample
                s = s.loc[(s.index >= start_dt) & (s.index <= end_dt)]
            except Exception:
                # If target_freq is invalid, fall back to unsampled series
                pass

        # Stable name
        s.name = getattr(ts, "code", code)
        return s

    except Exception as e:
        print(e)
        return pd.Series(name=code)


def Resample(
    series: pd.Series,
    freq: str = "ME",
) -> pd.Series:
    return series.resample(freq).last()


def PctChange(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    return series.pct_change(periods=periods).dropna()


def Diff(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    return series.diff(periods=periods)


def MovingAverage(
    series: pd.Series,
    window: int = 3,
) -> pd.Series:
    return series.rolling(window=window).mean()


def MonthEndOffset(
    series: pd.Series,
    months: int = 3,
) -> pd.Series:
    from pandas.tseries.offsets import MonthEnd

    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted + MonthEnd(0)
    return series


def MonthsOffset(
    series: pd.Series,
    months: int,
) -> pd.Series:
    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted
    return series


def Offset(
    series: pd.Series,
    months: int = 0,
    days: int = 0,
) -> pd.Series:
    shifted = series.index + pd.DateOffset(months=months, days=days)
    series.index = shifted
    return series


def StandardScalar(
    series: pd.Series,
    window: int = 20,
) -> pd.Series:
    roll = series.rolling(window=window)
    mean, std = roll.mean(), roll.std()
    return series.sub(mean).div(std).dropna()


def Clip(
    series: pd.Series,
    lower: Optional[float] = None,
    upper: Optional[float] = None,
) -> pd.Series:
    return series.clip(lower=lower, upper=upper)


def Ffill(series: pd.Series) -> pd.Series:
    return series.ffill()


import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from typing import Optional


def Cycle(series: pd.Series, max_points_per_cycle: Optional[int] = None) -> pd.Series:
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


import numpy as np


import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def find_best_window(series, max_lag=None):
    """
    Automatically find the dominant cycle length (best window size)
    using the autocorrelation function.
    """
    if max_lag is None:
        max_lag = min(365, len(series) // 2)  # sensible default for daily data
    ac = [series.autocorr(lag) for lag in range(1, max_lag)]
    best_window = np.argmax(ac) + 1  # +1 because lags start at 1
    return best_window


def CycleForecast(series: pd.Series, forecast_steps=12, window_size=None):
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


def Drawdown(series: pd.Series, window: int | None = None) -> pd.Series:
    if window:
        return series.div(series.rolling(window=window).max()).abs()
    return series.div(series.expanding().max()).abs()


def Rebase(series: pd.Series):
    return series / series.dropna().iloc[0]


def PMI_Manufacturing_Regime():
    manufacturing_pmis = [
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
    regimes = []
    for manufacturing_pmi in manufacturing_pmis:
        regime = core.Regime1(core.MACD(Series(manufacturing_pmi)).histogram).regime
        regimes.append(regime)

    regimes_df = pd.concat(regimes, axis=1)
    regime_counts = regimes_df.apply(
        lambda row: row.value_counts(normalize=True) * 100, axis=1
    )
    regime_pct = regime_counts.fillna(0).round(2)
    return regime_pct[["Expansion", "Slowdown", "Contraction", "Recovery"]].dropna()

def PMI_Services_Regime():
    manufacturing_pmis = [
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
        "NTCPMISVCBUSACTSA_BR:PX_LAST"

    ]
    regimes = []
    for manufacturing_pmi in manufacturing_pmis:
        regime = core.Regime1(core.MACD(Series(manufacturing_pmi)).histogram).regime
        regimes.append(regime)

    regimes_df = pd.concat(regimes, axis=1)
    regime_counts = regimes_df.apply(
        lambda row: row.value_counts(normalize=True) * 100, axis=1
    )
    regime_pct = regime_counts.fillna(0).round(2)
    regime_pct.index = pd.to_datetime(regime_pct.index)
    regime_pct = regime_pct.sort_index()
    return regime_pct[["Expansion", "Slowdown", "Contraction", "Recovery"]].dropna()


def FinancialConditionsIndex1() -> pd.Series:
    series = [
        StandardScalar(Series("VIX Index:PX_LAST"), 160),
        StandardScalar(Series("MOVE Index:PX_LAST"), 160),
        StandardScalar(Series("BAMLH0A0HYM2"), 160),
        StandardScalar(Series("BAMLC0A0CM"), 160),
    ]

    return pd.concat(series, axis=1).ffill().mean(axis=1)


def FedNetLiquidity() -> pd.Series:
    # 1) Load raw series
    asset_mil = Series("WALCL")  # millions USD
    treasury_bil = Series("WTREGEN")  # billions USD
    repo_bil = Series("RRPONTSYD")  # billions USD

    # 2) Normalize to trillions USD
    asset = asset_mil.div(1_000_000)  # → trillions
    treasury = treasury_bil.div(1_000)  # → trillions
    repo = repo_bil.div(1_000)  # → trillions
    # 3) Combine
    df = pd.concat({"asset": asset, "treasury": treasury, "repo": repo}, axis=1)
    # 4) Weekly on Wednesday, take last value & forward-fill
    weekly = df.resample("W-WED").last().ffill()
    # 5) Compute net liquidity
    weekly["net_liquidity_T"] = weekly["asset"] - weekly["treasury"] - weekly["repo"]
    daily = weekly["net_liquidity_T"].resample("B").ffill()
    return daily.dropna()


def NumOfPmiServicesPositiveMoM():
    manufacturing_pmis = [
        "NTCPMISVCBUSACTSA_WLD:PX_LAST",
        "NTCPMISVCBUSACTMESA_US:PX_LAST",
        "ISMNMI_NM:PX_LAST",
        "NTCPMISVCBUSACTSA_EUZ:PX_LAST",
        "NTCPMISVCBUSACTSA_DE:PX_LAST",
        "NTCPMISVCBUSACTSA_FR:PX_LAST",
        "NTCPMISVCBUSACTSA_IT:PX_LAST",
        "'NTCPMISVCBUSACTSA_ES",
        "NTCPMISVCBUSACTSA_GB:PX_LAST",
        "NTCPMISVCBUSACTSA_JP:PX_LAST",
        "NTCPMISVCBUSACTSA_CN:PX_LAST",
        "NTCPMISVCBUSACTSA_IN",
        "NTCPMISVCBUSACTSA_BR:PX_LAST"

    ]
    regimes = []
    for manufacturing_pmi in manufacturing_pmis:
        regimes.append(Series(manufacturing_pmi))
    regimes_df = pd.concat(regimes, axis=1)
    df_numeric = regimes_df.apply(pd.to_numeric, errors="coerce").diff()
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    percent_positive = percent_positive.sort_index()
    return percent_positive


def OecdCliRegime():
    manufacturing_pmis = [
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
    regimes = []
    for manufacturing_pmi in manufacturing_pmis:
        regime = core.Regime1(core.MACD(Series(manufacturing_pmi)).histogram).regime
        regimes.append(regime)

    regimes_df = pd.concat(regimes, axis=1)
    regime_counts = regimes_df.apply(
        lambda row: row.value_counts(normalize=True) * 100, axis=1
    )
    regime_pct = regime_counts.fillna(0).round(2)
    return regime_pct[["Expansion", "Slowdown", "Contraction", "Recovery"]].dropna()


def CustomSeries(code: str) -> pd.Series:
    if code == "GlobalGrowthRegime-Expansion":
        return PMI_Manufacturing_Regime()["Expansion"]

    if code == "GlobalGrowthRegime-Slowdown":
        return PMI_Manufacturing_Regime()["Slowdown"]

    if code == "GlobalGrowthRegime-Contraction":
        return PMI_Manufacturing_Regime()["Contraction"]

    if code == "GlobalGrowthRegime-Recovery":
        return PMI_Manufacturing_Regime()["Recovery"]

    if code == "NumOfOECDLeadingPositiveMoM":
        codes = [
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
        data = MultiSeries(*codes).diff()
        df_numeric = data.apply(pd.to_numeric, errors="coerce")
        positive_counts = (df_numeric > 0).sum(axis=1)
        valid_counts = df_numeric.notna().sum(axis=1)
        percent_positive = (positive_counts / valid_counts) * 100
        return percent_positive

    if code == "NumOfPmiPositiveMoM":
        codes = [
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
        data = MultiSeries(*codes).diff()
        df_numeric = data.apply(pd.to_numeric, errors="coerce")
        positive_counts = (df_numeric > 0).sum(axis=1)
        valid_counts = df_numeric.notna().sum(axis=1)
        percent_positive = (positive_counts / valid_counts) * 100
        return percent_positive

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
        from ix import get_timeseries

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
        return OecdCliRegime()["Expansion"]

    if code == "OecdCliRegime-Slowdown":
        return OecdCliRegime()["Slowdown"]

    if code == "OecdCliRegime-Contraction":
        return OecdCliRegime()["Contraction"]

    if code == "OecdCliRegime-Recovery":
        return OecdCliRegime()["Recovery"]


def NumofOecdCliMoMPositveEM():
    codes = [
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
    data = MultiSeries(*codes).diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    return percent_positive


def FinancialConditionsUS() -> pd.Series:
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

    dd.name = "FCI2"
    return dd


def FinancialConditionsKR():
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


def NumOfPmiPositiveMoM():
    codes = [
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
    data = MultiSeries(*codes).diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    return percent_positive


def USD_Open_Interest():
        data = Series("CFTNCLOI%ALLJUSDNYBTOF_US") - Series("CFTNCSOI%ALLJUSDNYBTOF_US")
        return data


def InvestorPositions():
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

def InvestorPositionsvsTrend(weeks: int = 52):
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

def NumOfOECDLeadingPositiveMoM():
    codes = [
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
    data = MultiSeries(*codes).diff()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    return percent_positive


class M2:

    def __init__(self, freq: str = 'ME', currency: str = "USD") -> None:
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
        series = (
            Series("GB.MAM2", freq=self.freq).div(1000_000).div(fx)
        )
        series.name = "UK"
        return series
    @property
    def CN(self) -> pd.Series:
        fx = Series("USDCNY Curncy:PX_LAST", freq=self.freq)
        series= Series("CN.MAM2", freq=self.freq).div(10_000).div(fx)
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
            [self.US, self.UK, self.EU, self.CN, self.JP, self.KR, self.CA, self.CH,],
            axis=1,
        ).ffill()
        return data.dropna()

    @property
    def WorldTotal(self) -> pd.Series:
        series = self.World.sum(axis=1).ffill()
        return series


def LocalIndices():
    from ix import get_timeseries

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
