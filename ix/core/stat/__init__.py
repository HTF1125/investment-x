from typing import Union
import numpy as np
import pandas as pd

from .preprocess import *


import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from typing import Optional


def Offset(
    series: pd.Series,
    months: int = 0,
    days: int = 0,
) -> pd.Series:
    shifted = series.index + pd.DateOffset(months=months, days=days)
    series.index = shifted
    return series


def StandardScaler(
    series: pd.Series,
    window: int = 20,
) -> pd.Series:
    roll = series.rolling(window=window)
    mean, std = roll.mean(), roll.std()
    return series.sub(mean).div(std).dropna()


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


def VAR(data: pd.Series, ddof: float = 1.0) -> float:
    return float(np.var(data, ddof=ddof))


def STDEV(data: pd.Series, ddof: float = 1.0) -> float:
    return np.sqrt(VAR(data=data, ddof=ddof))


def ENTP(data: pd.Series, base: float = 2.0) -> float:
    """Entropy (ENTP)

    Introduced by Claude Shannon in 1948, entropy measures the unpredictability
    of the data, or equivalently, of its average information. A die has higher
    entropy (p=1/6) versus a coin (p=1/2).

    Sources:
        https://en.wikipedia.org/wiki/Entropy_(information_theory)
    """
    p = data / data.sum()
    entropy = (-p * np.log(p) / np.log(base)).sum()
    return entropy


def CV(data: pd.Series) -> float:
    return data.std() / data.mean()


def Winsorize(data: pd.Series, lower: float = -3.0, upper: float = 3.0) -> pd.Series:
    return data.clip(lower, upper)


def empirical_cov(
    x1: Union[np.ndarray, pd.Series],
    x2: Union[np.ndarray, pd.Series],
) -> float:
    assert len(x1) == len(x2), "x1 and x2 musth be the same length"
    n = len(x1)
    mean1, mean2 = x1.mean(), x2.mean()
    cov = float(np.sum(((x1 - mean1) * (x2 - mean2)))) / (n - 1)
    return cov
