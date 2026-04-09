"""Elliott Wave detection and TD Sequential indicator.

Pure computation functions extracted from the technical analysis router.
No FastAPI/HTTP dependencies — only numpy, pandas, and typing.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


class TDSequentialClean:
    def __init__(
        self,
        show_setup_from: int = 9,
        show_countdown_from: int = 13,
        label_cooldown_bars: int = 0,
        setup_lookback: int = 4,
        setup_len: int = 9,
        countdown_lookback: int = 2,
        countdown_len: int = 13,
        suppress_setup_when_cd_active: bool = False,
        cancel_on_opposite_setup9: bool = True,
    ):
        self.show_setup_from = show_setup_from
        self.show_countdown_from = show_countdown_from
        self.label_cooldown_bars = label_cooldown_bars
        self.setup_lookback = setup_lookback
        self.setup_len = setup_len
        self.countdown_lookback = countdown_lookback
        self.countdown_len = countdown_len
        self.suppress_setup_when_cd_active = suppress_setup_when_cd_active
        self.cancel_on_opposite_setup9 = cancel_on_opposite_setup9

    def _cooldown_mask(self, base_mask: pd.Series) -> pd.Series:
        if self.label_cooldown_bars <= 0:
            return base_mask
        keep = np.zeros(len(base_mask), dtype=bool)
        cooldown = 0
        for i, flag in enumerate(base_mask.to_numpy()):
            if cooldown > 0:
                cooldown -= 1
                continue
            if flag:
                keep[i] = True
                cooldown = self.label_cooldown_bars
        return pd.Series(keep, index=base_mask.index)

    def compute(self, close: pd.Series) -> pd.DataFrame:
        close = pd.to_numeric(close, errors="coerce").astype(float).dropna().sort_index()
        if len(close) < 20:
            raise ValueError("close series too short")
        n = len(close)
        bear_cond = close > close.shift(self.setup_lookback)
        bull_cond = close < close.shift(self.setup_lookback)
        bear_setup = np.zeros(n, dtype=int)
        bull_setup = np.zeros(n, dtype=int)
        bs = us = 0
        for i in range(n):
            bs = bs + 1 if bool(bear_cond.iloc[i]) else 0
            us = us + 1 if bool(bull_cond.iloc[i]) else 0
            bear_setup[i] = bs if 1 <= bs <= self.setup_len else 0
            bull_setup[i] = us if 1 <= us <= self.setup_len else 0

        bear_cd_cond = close >= close.shift(self.countdown_lookback)
        bull_cd_cond = close <= close.shift(self.countdown_lookback)
        bear_cd = np.zeros(n, dtype=int)
        bull_cd = np.zeros(n, dtype=int)
        bear_cd_active = np.zeros(n, dtype=bool)
        bull_cd_active = np.zeros(n, dtype=bool)
        bear_active = bull_active = False
        bear_count = bull_count = 0
        for i in range(n):
            if bear_setup[i] == self.setup_len:
                bear_active = True
                bear_count = 0
                if self.cancel_on_opposite_setup9:
                    bull_active = False
                    bull_count = 0
            if bull_setup[i] == self.setup_len:
                bull_active = True
                bull_count = 0
                if self.cancel_on_opposite_setup9:
                    bear_active = False
                    bear_count = 0
            bear_cd_active[i] = bear_active
            bull_cd_active[i] = bull_active
            if bear_active:
                if bear_count < self.countdown_len and bool(bear_cd_cond.iloc[i]):
                    bear_count += 1
                bear_cd[i] = bear_count
                if bear_count >= self.countdown_len:
                    bear_active = False
            if bull_active:
                if bull_count < self.countdown_len and bool(bull_cd_cond.iloc[i]):
                    bull_count += 1
                bull_cd[i] = bull_count
                if bull_count >= self.countdown_len:
                    bull_active = False

        return pd.DataFrame(
            {
                "close": close,
                "bear_setup": bear_setup,
                "bull_setup": bull_setup,
                "bear_cd": bear_cd,
                "bull_cd": bull_cd,
                "bear_cd_active": bear_cd_active,
                "bull_cd_active": bull_cd_active,
            },
            index=close.index,
        )


def _find_swings(df: pd.DataFrame, window: int) -> pd.DataFrame:
    high = df["High"]
    low = df["Low"]
    if isinstance(high, pd.DataFrame):
        high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame):
        low = low.iloc[:, 0]
    is_high = high.eq(high.rolling(window * 2 + 1, center=True).max())
    is_low = low.eq(low.rolling(window * 2 + 1, center=True).min())
    points = []
    for i in range(len(df)):
        d = df.index[i]
        if bool(is_high.iloc[i]):
            points.append((d, float(high.iloc[i]), "H"))
        if bool(is_low.iloc[i]):
            points.append((d, float(low.iloc[i]), "L"))
    if not points:
        return pd.DataFrame(columns=["Date", "Price", "Type"])
    swings = pd.DataFrame(points, columns=["Date", "Price", "Type"]).sort_values("Date")
    cleaned = []
    for _, p in swings.iterrows():
        if not cleaned:
            cleaned.append(p)
            continue
        last = cleaned[-1]
        if p["Type"] == last["Type"]:
            if (p["Type"] == "H" and p["Price"] > last["Price"]) or (p["Type"] == "L" and p["Price"] < last["Price"]):
                cleaned[-1] = p
        else:
            cleaned.append(p)
    return pd.DataFrame(cleaned)


def _wave_labels(n: int) -> list[str]:
    seq = ["(1)", "(2)", "(3)", "(4)", "(5)", "(a)", "(b)", "(c)"]
    return seq[:n] if n <= len(seq) else seq + [f"({i})" for i in range(6, 6 + n - len(seq))]

def _alternates_types(types: list[str]) -> bool:
    return all(types[i] != types[i - 1] for i in range(1, len(types)))


def _score_to_target(value: float, target: float, spread: float) -> float:
    if spread <= 0 or not np.isfinite(value):
        return 0.0
    return max(0.0, 1.0 - abs(value - target) / spread)


def _evaluate_motive(prices: np.ndarray, types: list[str], bullish: bool) -> tuple[bool, float]:
    # Contiguous 6 pivots: p0..p5 define waves 1..5.
    p0, p1, p2, p3, p4, p5 = [float(x) for x in prices]
    tol = max((max(prices) - min(prices)) * 0.005, 1e-9)

    if bullish:
        if types != ["L", "H", "L", "H", "L", "H"]:
            return False, float("-inf")
        w1 = p1 - p0
        w2 = p1 - p2
        w3 = p3 - p2
        w4 = p3 - p4
        w5 = p5 - p4
        if min(w1, w2, w3, w4, w5) <= 0:
            return False, float("-inf")
        if p2 <= p0 + tol:
            return False, float("-inf")
        if p4 < p1 - tol:
            return False, float("-inf")
        if p5 <= p3 + tol * 0.3:
            return False, float("-inf")
        if w3 < min(w1, w5) + tol:
            return False, float("-inf")
    else:
        if types != ["H", "L", "H", "L", "H", "L"]:
            return False, float("-inf")
        w1 = p0 - p1
        w2 = p2 - p1
        w3 = p2 - p3
        w4 = p4 - p3
        w5 = p4 - p5
        if min(w1, w2, w3, w4, w5) <= 0:
            return False, float("-inf")
        if p2 >= p0 - tol:
            return False, float("-inf")
        if p4 > p1 + tol:
            return False, float("-inf")
        if p5 >= p3 - tol * 0.3:
            return False, float("-inf")
        if w3 < min(w1, w5) + tol:
            return False, float("-inf")

    r2 = w2 / w1
    r4 = w4 / w3
    ext3 = w3 / w1
    ext5 = w5 / w1
    if not (0.15 <= r2 <= 0.95):
        return False, float("-inf")
    if not (0.10 <= r4 <= 0.90):
        return False, float("-inf")
    if ext3 < 1.0 or ext5 < 0.20:
        return False, float("-inf")

    impulse_legs = np.array([w1, w3, w5], dtype=float)
    if impulse_legs.min() < impulse_legs.max() * 0.12:
        return False, float("-inf")

    displacement = abs(p5 - p0) / (impulse_legs.sum() + 1e-9)
    score = 2.0
    score += _score_to_target(r2, target=0.618, spread=0.50)
    score += _score_to_target(r4, target=0.382, spread=0.35)
    score += _score_to_target(ext3, target=1.618, spread=1.10)
    score += _score_to_target(ext5, target=1.000, spread=0.90)
    score += min(1.0, displacement)
    return True, score


def _valid_motive(prices: np.ndarray, types: list[str], bullish: bool) -> bool:
    valid, _ = _evaluate_motive(prices, types, bullish)
    return valid


def _find_motive_segment(piv: pd.DataFrame, max_lookback: int = 120) -> tuple[int, bool, float] | None:
    if len(piv) < 6:
        return None
    recent = piv.tail(max_lookback).reset_index(drop=True)
    offset = len(piv) - len(recent)
    pivot_scale = np.nanmedian(np.abs(np.diff(recent["Price"].to_numpy(dtype=float))))
    if not np.isfinite(pivot_scale) or pivot_scale <= 0:
        pivot_scale = 1.0
    candidates: list[tuple[int, bool, float]] = []
    for i in range(0, len(recent) - 5):
        seg = recent.iloc[i : i + 6]
        types = seg["Type"].tolist()
        if not _alternates_types(types):
            continue
        prices = seg["Price"].to_numpy(dtype=float)
        for bullish in (True, False):
            valid, base_score = _evaluate_motive(prices, types, bullish)
            if valid:
                displacement = abs(float(prices[-1] - prices[0])) / pivot_scale
                recency = (i + 5) / max(6, len(recent))
                total_score = base_score + min(3.0, displacement * 0.20) + recency * 0.60
                candidates.append((i, bullish, total_score))
    if not candidates:
        return None
    # Prefer strongest structure score, then latest start.
    candidates.sort(key=lambda x: (x[2], x[0]), reverse=True)
    start_idx, bullish, total_score = candidates[0]
    return (start_idx + offset, bullish, total_score)


def _evaluate_abc(prices: np.ndarray, types: list[str], bullish_motive: bool) -> tuple[bool, float]:
    a, b, c, d = [float(x) for x in prices]  # d is prior wave-5 pivot
    tol = max(abs(d - a) * 0.005, 1e-9)
    if bullish_motive:
        # after bullish motive ends at high d, correction is L-H-L
        if types != ["L", "H", "L"]:
            return False, float("-inf")
        if not (a < d - tol and b < d - tol and c < b - tol * 0.2):
            return False, float("-inf")
        if c > a + tol:
            return False, float("-inf")
        leg1 = d - a
        leg2 = b - a
        leg3 = b - c
    else:
        # after bearish motive ends at low d, correction is H-L-H
        if types != ["H", "L", "H"]:
            return False, float("-inf")
        if not (a > d + tol and b > d + tol and c > b + tol * 0.2):
            return False, float("-inf")
        if c < a - tol:
            return False, float("-inf")
        leg1 = a - d
        leg2 = a - b
        leg3 = c - b

    if min(leg1, leg2, leg3) <= 0:
        return False, float("-inf")
    retr_b = leg2 / leg1
    ext_c = leg3 / leg2
    if not (0.15 <= retr_b <= 0.95):
        return False, float("-inf")
    if not (0.40 <= ext_c <= 2.80):
        return False, float("-inf")

    score = 1.0
    score += _score_to_target(retr_b, target=0.618, spread=0.45)
    score += _score_to_target(ext_c, target=1.000, spread=0.90)
    if bullish_motive and c <= a - tol:
        score += 0.40
    if (not bullish_motive) and c >= a + tol:
        score += 0.40
    return True, score


def _valid_abc(prices: np.ndarray, types: list[str], bullish_motive: bool) -> bool:
    valid, _ = _evaluate_abc(prices, types, bullish_motive)
    return valid


def _best_abc_after_motive(
    piv: pd.DataFrame,
    motive_end_idx: int,
    bullish_motive: bool,
    max_forward: int = 8,
) -> tuple[pd.DataFrame | None, float]:
    if motive_end_idx + 3 > len(piv):
        return None, float("-inf")
    start_min = motive_end_idx + 1
    start_max = min(len(piv) - 3, motive_end_idx + max_forward)
    if start_min > start_max:
        return None, float("-inf")

    last_p5 = float(piv["Price"].iloc[motive_end_idx])
    best: tuple[pd.DataFrame, float] | None = None
    for start in range(start_min, start_max + 1):
        abc = piv.iloc[start : start + 3].copy()
        abc_prices = np.array(
            [float(abc["Price"].iloc[0]), float(abc["Price"].iloc[1]), float(abc["Price"].iloc[2]), last_p5]
        )
        abc_types = abc["Type"].tolist()
        valid, base_score = _evaluate_abc(abc_prices, abc_types, bullish_motive=bullish_motive)
        if not valid:
            continue
        delay_penalty = (start - start_min) * 0.08
        total = base_score - delay_penalty
        if best is None or total > best[1]:
            best = (abc, total)

    if best is None:
        return None, float("-inf")
    return best


def _extract_elliott_labels(
    piv: pd.DataFrame,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, bool | None, float]:
    found = _find_motive_segment(piv)
    if found is None:
        return None, None, None, float("-inf")
    start, bullish, motive_score = found
    motive = piv.iloc[start : start + 6].copy()
    correction, correction_score = _best_abc_after_motive(
        piv=piv,
        motive_end_idx=start + 5,
        bullish_motive=bullish,
    )
    total_score = motive_score + (correction_score if correction is not None else 0.0)
    return motive, correction, bullish, total_score


def _extract_best_elliott(
    swings_map: Dict[int, pd.DataFrame]
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, bool | None, int | None]:
    degree_bias = {4: 0.05, 8: 0.20, 16: 0.15}
    best: tuple[float, int, pd.DataFrame, pd.DataFrame | None, bool] | None = None
    for length, piv in swings_map.items():
        if piv is None or len(piv) < 6:
            continue
        motive, correction, bullish, score = _extract_elliott_labels(piv)
        if motive is None or bullish is None:
            continue
        adjusted = score + degree_bias.get(length, 0.0)
        if best is None or adjusted > best[0]:
            best = (adjusted, length, motive, correction, bullish)
    if best is None:
        return None, None, None, None
    _, length, motive, correction, bullish = best
    return motive, correction, bullish, length
