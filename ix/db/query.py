from typing import Optional
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from ix.db.models import Timeseries


def MultiSeries(*codes: str | list[str] | dict) -> pd.DataFrame:
    output = []
    for code in codes:
        if isinstance(code, str):
            output.append(Series(code))
        elif isinstance(code, list):
            output.append(Series(*code))
        elif isinstance(code, dict):
            for k, v in code.items():
                s = Series(v)
                s.name = k
                output.append(s)
    return pd.concat(output, axis=1)


def Series(code: str) -> pd.Series:
    ts = Timeseries.find_one({"code": code}).run()
    if ts is not None:
        return ts.data
    try:
        data = eval(code)
        assert isinstance(data, pd.Series)
        data.name = code
        return data
    except:
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
        popt, pcov = curve_fit(sine_model, t, y, p0=p0, bounds=bounds, max_nfev=10000)
    else:
        popt, pcov = curve_fit(sine_model, t, y, p0=p0, max_nfev=10000)

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
