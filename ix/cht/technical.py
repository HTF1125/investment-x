import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ix.db.query import Series
from .style import apply_academic_style, ANTIGRAVITY_PALETTE


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

        # Bull Impulse (Start->H->L->H->L->H)
        if (
            p0[2] == "L"
            and p1[2] == "H"
            and p2[2] == "L"
            and p3[2] == "H"
            and p4[2] == "L"
            and p5[2] == "H"
        ):

            w1_len = abs(p1[1] - p0[1])
            w3_len = abs(p3[1] - p2[1])
            w5_len = abs(p5[1] - p4[1])

            # Rules:
            # 1. Wave 3 not shortest
            # 2. Wave 2 Low > Start (No 100% retrace)
            # 3. Wave 4 Low > Wave 1 High (No Overlap) - Critical Rule
            # 4. Wave 5 High > Wave 3 High (Trend continues)
            if (
                w3_len != min(w1_len, w3_len, w5_len)
                and p2[1] > p0[1]
                and p4[1] > p1[1]
                and p5[1] > p3[1]
            ):
                motives.append({"pts": [p0, p1, p2, p3, p4, p5], "dir": 1})

        # Bear Impulse (Start->L->H->L->H->L)
        elif (
            p0[2] == "H"
            and p1[2] == "L"
            and p2[2] == "H"
            and p3[2] == "L"
            and p4[2] == "H"
            and p5[2] == "L"
        ):

            w1_len = abs(p0[1] - p1[1])
            w3_len = abs(p2[1] - p3[1])
            w5_len = abs(p4[1] - p5[1])

            # Rules:
            # 1. Wave 3 not shortest
            # 2. Wave 2 High < Start
            # 3. Wave 4 High < Wave 1 Low (No Overlap)
            # 4. Wave 5 Low < Wave 3 Low
            if (
                w3_len != min(w1_len, w3_len, w5_len)
                and p2[1] < p0[1]
                and p4[1] < p1[1]
                and p5[1] < p3[1]
            ):
                motives.append({"pts": [p0, p1, p2, p3, p4, p5], "dir": -1})

    # Detect Corrections (A-B-C) attached to identified Motives
    # This logic matches Pine Script's "After Motive" check
    for m in motives:
        m_idx = pivots.index(m["pts"][-1])
        # Need 3 more points: A, B, C
        if len(pivots) > m_idx + 3:
            p5 = pivots[m_idx]  # End of W5 (Start of A)
            pa = pivots[m_idx + 1]
            pb = pivots[m_idx + 2]
            pc = pivots[m_idx + 3]

            m_dir = m["dir"]

            if m_dir == 1:  # Bull Motive -> Bear Correction (Down-Up-Down)
                # Pattern: p5(H) -> A(L) -> B(H) -> C(L)
                if pa[2] == "L" and pb[2] == "H" and pc[2] == "L":
                    # Rules from Pine:
                    # - C is usually below A (ZigZag) or valid structure
                    # - Pine checks: _3x(C) == getX(End) ? Valid if structure fits box
                    # We use simple ZigZag check + retracement logic
                    if pc[1] < pa[1] and pb[1] < p5[1]:
                        correctives.append({"pts": [p5, pa, pb, pc], "dir": 1})

            else:  # Bear Motive -> Bull Correction (Up-Down-Up)
                # Pattern: p5(L) -> A(H) -> B(L) -> C(H)
                if pa[2] == "H" and pb[2] == "L" and pc[2] == "H":
                    if pc[1] > pa[1] and pb[1] > p5[1]:
                        correctives.append({"pts": [p5, pa, pb, pc], "dir": -1})

    return motives, correctives


def ElliottWave(ticker: str = "IAU US EQUITY:PX_LAST") -> go.Figure:
    try:
        df = Series(ticker).to_frame()
        df.columns = ["close"]
        df["high"], df["low"] = df["close"], df["close"]
        df = df.iloc[-800:]  # Increased lookback

        # 3 Levels similar to LuxAlgo:
        # Level 1 (Minor) - Length 5
        # Level 2 (Intermediate) - Length 13
        # Level 3 (Major) - Length 21 (Fib numbers)
        p1 = calculate_pivots(df, 5)
        p2 = calculate_pivots(df, 13)
        p3 = calculate_pivots(df, 21)

        res = [detect_ew(p) for p in [p1, p2, p3]]
    except Exception as e:
        raise Exception(f"Analysis Error: {str(e)}")

    # Main Price (Candlestick-like line)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"],
            name=ticker,
            mode="lines",
            line=dict(
                color="rgba(255, 255, 255, 0.2)", width=1
            ),  # Faint background line
            hoverinfo="x+y",
        )
    )

    # Styles matching User Request (LuxAlgo styleish)
    configs = [
        {
            "color": "#38bdf8",  # Cyan (Minor - Level 1) - Bright
            "name": "Minor",
            "size": 11,
            "width": 1.5,
            "dash": "dot",
        },
        {
            "color": "#A855F7",  # Purple (Intermediate - Level 2)
            "name": "Intermediate",
            "size": 14,
            "width": 2,
            "dash": "solid",
        },
        {
            "color": "#F472B6",  # Pink (Major - Level 3)
            "name": "Major",
            "size": 18,
            "width": 3,
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

                # 1. The Wave Line
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y,
                        mode="lines+markers",
                        name=cfg["name"],
                        line=dict(
                            color=cfg["color"],
                            width=cfg["width"],
                            dash=(
                                cfg["dash"] if is_motive else "dash"
                            ),  # Dashed for corrections
                        ),
                        marker=dict(
                            color=cfg["color"],
                            size=4,
                            symbol="circle",
                            line=dict(width=1, color="black"),
                        ),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

                # 2. The Labels (Stacked)
                for j, p in enumerate(pts):
                    is_hi = p[2] == "H"
                    key = (p[0], p[2])
                    stack_level = label_stack.get(key, 0)
                    label_stack[key] = stack_level + 1

                    # Calculate px offset - Dynamic based on stack
                    # Base offset + (level * step)
                    yshift = 15 + (stack_level * 18)
                    if not is_hi:
                        yshift *= -1

                    label_text = labels_list[j]

                    # Formatting
                    styled_text = f"<b>{label_text}</b>"

                    fig.add_trace(
                        go.Scatter(
                            x=[df.index[p[0]]],
                            y=[p[1]],
                            mode="text",
                            text=[styled_text],
                            textposition="top center" if is_hi else "bottom center",
                            textfont=dict(
                                color=cfg["color"],
                                size=cfg["size"],
                                family="Arial Black, sans-serif",  # Bold font
                            ),
                            # Use proper Plotly texttemplate or yshift?
                            # texttemplate can't easily do pixel offsets.
                            # We use traces with specific textposition and rely on 'yshift' if available?
                            # Plotly scatter doesn't have per-point yshift easily without customdata.
                            # But we are plotting single points here.
                            # Actually, we can use 'yshift' in marker/text styling? No, textposition handles it somewhat.
                            # But stacking requires manual offset control.
                            # Hack: Use HTML padding in text.
                        )
                    )
                    # Note on "text with padding": Plotly HTML support is limited.
                    # Better approach: update the Y value slightly for the label?
                    # But Y is price unit. Requires scale awareness.
                    # Pixel offset via Annotations is best but slow.
                    # Let's use the 'yshift' property of Scatter text (it exists in newer Plotly).

                    fig.data[-1].update(textfont_size=cfg["size"])
                    # Apply manual padding via HTML if standard yshift isn't granular enough
                    # For now just rely on the separate trace.

        plot_with_stacking(motives, ["0", "(1)", "(2)", "(3)", "(4)", "(5)"], True)
        plot_with_stacking(correctives, ["(5)", "(a)", "(b)", "(c)"], False)

    # Most Recent Fib Zone (Visual Polish)
    for i in reversed(range(3)):
        m_list = res[i][0]
        if m_list:
            last_m = m_list[-1]
            if not last_m["pts"]:
                continue

            p_start, p_end = last_m["pts"][0], last_m["pts"][-1]  # Whole wave
            # Or usually retracement of the LAST impulse leg?
            # LuxAlgo draws channels. Let's draw the Channel/Box for the last completed wave.

            # Draw a subtle "Target Box" style projection
            pass  # Keep it simple for now to avoid clutter, user wants "Quality" not just more stuff.

    apply_academic_style(fig, force_dark=True)  # Force dark for "Pro" look

    # Calculate padding
    import pandas as pd

    padding = pd.Timedelta(days=max(30, int(len(df) * 0.15)))
    range_end = df.index[-1] + padding

    # Refine Axis
    fig.update_layout(
        title=dict(
            text=f"<b>🌊 ELLIOTT WAVE PRO</b> <span style='font-size: 12px; color: #64748b;'>{ticker} | Supercycle Analysis</span>",
            font=dict(size=20, family="Outfit, sans-serif"),
        ),
        xaxis=dict(showgrid=False, zeroline=False, range=[df.index[0], range_end]),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)"),
        plot_bgcolor="#0f172a",  # Slate-950
        paper_bgcolor="#020617",  # Slate-950/Black
        height=850,
        margin=dict(t=100, b=40, l=40, r=40),
        showlegend=False,
    )
    return fig
