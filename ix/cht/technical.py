import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ix.db.query import Series
from .style import apply_academic_style


def calculate_pivots(df: pd.DataFrame, left: int, right: int = 1):
    """
    Pine Script ta.pivothigh/ta.pivotlow style detection.
    A pivot is found at index 'i' if it is the extreme in [i-left, i+right].
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    pivots = []

    for i in range(left, n - right):
        # Pivot High
        is_hi = True
        for j in range(i - left, i + right + 1):
            if highs[j] > highs[i]:
                is_hi = False
                break
        if is_hi:
            pivots.append((i, highs[i], "H"))

        # Pivot Low
        is_lo = True
        for j in range(i - left, i + right + 1):
            if lows[j] < lows[i]:
                is_lo = False
                break
        if is_lo:
            pivots.append((i, lows[i], "L"))

    if not pivots:
        return []

    # Alternation Filter
    pivots.sort(key=lambda x: x[0])
    filtered = [pivots[0]]
    for i in range(1, len(pivots)):
        prev, curr = filtered[-1], pivots[i]
        if curr[2] == prev[2]:
            if (curr[2] == "H" and curr[1] > prev[1]) or (
                curr[2] == "L" and curr[1] < prev[1]
            ):
                filtered[-1] = curr
        else:
            filtered.append(curr)
    return filtered


def detect_ew(pivots):
    motives, correctives = [], []
    for i in range(len(pivots) - 5):
        p0, p1, p2, p3, p4, p5 = pivots[i : i + 6]
        # Bull
        if p1[2] == "H":
            w1, w3, w5 = (p1[1] - p0[1]), (p3[1] - p2[1]), (p5[1] - p4[1])
            if (
                w1 > 0
                and w3 > 0
                and w5 > 0
                and w3 != min(w1, w3, w5)
                and p3[1] > p1[1]
                and p2[1] > p0[1]
                and p4[1] > p2[1]
            ):
                motives.append({"pts": [p0, p1, p2, p3, p4, p5], "dir": 1})
        # Bear
        elif p1[2] == "L":
            w1, w3, w5 = (p0[1] - p1[1]), (p2[1] - p3[1]), (p4[1] - p5[1])
            if (
                w1 > 0
                and w3 > 0
                and w5 > 0
                and w3 != min(w1, w3, w5)
                and p3[1] < p1[1]
                and p2[1] < p0[1]
                and p4[1] < p2[1]
            ):
                motives.append({"pts": [p0, p1, p2, p3, p4, p5], "dir": -1})

    for m in motives:
        m_idx = pivots.index(m["pts"][-1])
        if len(pivots) > m_idx + 3:
            p5, pa, pb, pc = (
                pivots[m_idx],
                pivots[m_idx + 1],
                pivots[m_idx + 2],
                pivots[m_idx + 3],
            )
            if m["dir"] == 1:
                # Bullish correction (A-B-C down)
                if (
                    pa[2] == "L"
                    and pb[2] == "H"
                    and pc[2] == "L"
                    and pb[1] < p5[1]
                    and pc[1] < pa[1]
                ):
                    correctives.append({"pts": [p5, pa, pb, pc], "dir": 1})
            else:
                # Bearish correction (A-B-C up)
                if (
                    pa[2] == "H"
                    and pb[2] == "L"
                    and pc[2] == "H"
                    and pb[1] > p5[1]
                    and pc[1] > pa[1]
                ):
                    correctives.append({"pts": [p5, pa, pb, pc], "dir": -1})
    return motives, correctives


def ElliottWave(ticker: str = "IAU US EQUITY:PX_LAST") -> go.Figure:
    try:
        df = Series(ticker).to_frame()
        df.columns = ["close"]
        df["high"], df["low"] = df["close"], df["close"]
        df = df.iloc[-500:]

        # 3 Levels: 4, 8, 16
        p1 = calculate_pivots(df, 4)
        p2 = calculate_pivots(df, 8)
        p3 = calculate_pivots(df, 16)

        res = [detect_ew(p) for p in [p1, p2, p3]]
    except Exception as e:
        raise Exception(f"Analysis Error: {str(e)}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"],
            name=ticker,
            mode="lines",
            line=dict(color="#475569", width=1.5),
            opacity=0.7,
        )
    )

    configs = [
        {
            "color": ANTIGRAVITY_PALETTE[0],
            "name": "Minor",
            "size": 11,
            "width": 1.5,
            "dash": "dot",
        },
        {
            "color": ANTIGRAVITY_PALETTE[1],
            "name": "Intermediate",
            "size": 13,
            "width": 2,
            "dash": "solid",
        },
        {
            "color": ANTIGRAVITY_PALETTE[4],
            "name": "Major",
            "size": 15,
            "width": 2.5,
            "dash": "solid",
        },
    ]

    # To track stack levels: (index, direction) -> stack_count
    label_stack = {}

    for i, (motives, correctives) in enumerate(res):
        cfg = configs[i]

        # Helper to plot with stacking
        def plot_with_stacking(patterns, labels_list, is_motive=True):
            for patt in patterns:
                pts = patt["pts"]
                x = [df.index[p[0]] for p in pts]
                y = [p[1] for p in pts]

                # Plot lines
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y,
                        mode="lines",
                        name=cfg["name"],
                        line=dict(
                            color=cfg["color"],
                            width=cfg["width"],
                            dash=cfg["dash"] if is_motive else "dash",
                        ),
                        hoverinfo="skip",
                    )
                )

                # Plot labels with stacking
                for j, p in enumerate(pts):
                    is_hi = p[2] == "H"
                    key = (p[0], p[2])
                    stack_level = label_stack.get(key, 0)
                    label_stack[key] = stack_level + 1

                    # Calculate px offset
                    yshift = (stack_level * 16) + 12
                    if not is_hi:
                        yshift *= -1

                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[p[0]]],
                            y=[p[1]],
                            mode="text",
                            text=[labels_list[j]],
                            textposition="middle center",
                            textfont=dict(
                                color=cfg["color"],
                                size=cfg["size"],
                                family="Outfit Bold",
                            ),
                            # Plotly text-only trace with no markers, using yshift for stacking
                            texttemplate=(
                                f"<span style='padding-bottom:{yshift}px'>{labels_list[j]}</span>"
                                if is_hi
                                else f"<span style='padding-top:{abs(yshift)}px'>{labels_list[j]}</span>"
                            ),
                            cliponaxis=False,
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )

        plot_with_stacking(motives, ["0", "(1)", "(2)", "(3)", "(4)", "(5)"], True)
        plot_with_stacking(correctives, ["(5)", "(a)", "(b)", "(c)"], False)

    # Most Recent Fib Zone
    for i in reversed(range(3)):
        m_list = res[i][0]
        if m_list:
            last_m = m_list[-1]
            p1, p2 = last_m["pts"][1], last_m["pts"][2]  # Retracement of Wave 1
            diff = abs(last_m["pts"][1][1] - last_m["pts"][0][1])
            for lvl, opac in [(0.5, 0.05), (0.618, 0.1), (0.764, 0.15)]:
                v = (
                    last_m["pts"][1][1] - (diff * lvl)
                    if last_m["dir"] == 1
                    else last_m["pts"][1][1] + (diff * lvl)
                )
                fig.add_shape(
                    type="rect",
                    x0=df.index[last_m["pts"][1][0]],
                    x1=df.index[-1],
                    y0=v,
                    y1=v + (diff * 0.015),
                    fillcolor=configs[i]["color"],
                    opacity=opac,
                    line_width=0,
                )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(
            text=f"<b>PRO-LEVEL ELLIOTT WAVE ANALYSIS</b><br><span style='font-size: 11px; font-weight: normal; color: #94a3b8;'>{ticker} | Minor(4), Intermediate(8), Major(16)</span>"
        ),
        yaxis_title="Market Price",
        showlegend=False,
        height=850,
        margin=dict(t=130),
    )
    return fig
