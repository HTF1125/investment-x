from typing import Optional
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from ix.db.models import Timeseries
from cachetools import TTLCache, cached
from ix import core

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


def Series(code: str, freq: str | None = None) -> pd.Series:
    try:
        ts = Timeseries.find_one({"code": code}).run()
        if ts is not None:
            data = ts.data
            if freq:
                data = data.resample(freq).last()
            return data
    except:
        pass

    try:
        if "=" in code:
            name, new_code = code.split("=", maxsplit=1)

            data = eval(new_code)
            assert isinstance(data, pd.Series)
            data.name = name
        else:
            data = eval(code)
        assert isinstance(data, pd.Series)
        if freq:
            data = data.resample(freq).last().ffill()
        return data
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


def GlobalGrowthRegime():
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
    asset_mil    = Series('WALCL')      # millions USD
    treasury_bil = Series('WTREGEN')    # billions USD
    repo_bil     = Series('RRPONTSYD')  # billions USD

    # 2) Normalize to trillions USD
    asset   = asset_mil.div(1_000_000)  # → trillions
    treasury= treasury_bil.div(1_000)   # → trillions
    repo    = repo_bil.div(1_000)       # → trillions
    # 3) Combine
    df = pd.concat({
        'asset'   : asset,
        'treasury': treasury,
        'repo'    : repo
    }, axis=1)
    # 4) Weekly on Wednesday, take last value & forward-fill
    weekly = df.resample('W-WED').last().ffill()
    # 5) Compute net liquidity
    weekly['net_liquidity_T'] = (
        weekly['asset']
      - weekly['treasury']
      - weekly['repo']
    )
    daily = weekly['net_liquidity_T'].resample("B").ffill()
    return daily.dropna()


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
        return GlobalGrowthRegime()["Expansion"]

    if code == "GlobalGrowthRegime-Slowdown":
        return GlobalGrowthRegime()["Slowdown"]

    if code == "GlobalGrowthRegime-Contraction":
        return GlobalGrowthRegime()["Contraction"]

    if code == "GlobalGrowthRegime-Recovery":
        return GlobalGrowthRegime()["Recovery"]

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

        data = pd.concat([
            Series('US.MAM2').dropna()/1000,
            Series('EUZ.MAM2')*Resample(Series('EURUSD Curncy:PX_LAST'), 'ME').dropna()/1000/1000,
            Series('GB.MAM2')/Resample(Series('USDGBP Curncy:PX_LAST'), 'ME').dropna()/1000/1000,
            Series('JP.MAM2')/Resample(Series('USDJPY Curncy:PX_LAST'), 'ME').dropna()/10/1000,
            Series('CN.MAM2')/Resample(Series('USDCNY Curncy:PX_LAST'), 'ME').dropna()/10/1000,
        ], axis=1).dropna()
        data =  data.sum(axis=1).dropna()
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
