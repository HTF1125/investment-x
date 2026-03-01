"""
전시 S&P 500 / 금 / WTI 원유 성과 분석 — Streamlit 앱
주요 지정학적 갈등 발생 후 200거래일 시장 반응을 분석합니다.
"""

import tempfile
from collections import namedtuple
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from fpdf import FPDF

from ix import Series

# ---------------------------------------------------------------------------
# 페이지 설정
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="전시 증시 분석",
    page_icon="⚔️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# 갈등 데이터
# ---------------------------------------------------------------------------
CONFLICTS = {
    "걸프전 (1990)":                  ("1990-08-02", None),
    "코소보/NATO 공습 (1999)":         ("1999-03-24", None),
    "9/11 테러 / 아프가니스탄 (2001)": ("2001-09-11", None),
    "이라크 전쟁 침공 (2003)":         ("2003-03-20", None),
    "리비아/아랍의 봄 (2011)":         ("2011-02-15", None),
    "ISIS/이라크 위기 (2014)":         ("2014-06-04", None),
    "미국-시리아 공습 (2017)":         ("2017-04-07", None),
    "솔레이마니/이란 공습 (2020)*":    ("2020-01-03", "⚠️ COVID-19 팬데믹과 동시 발생"),
    "러시아-우크라이나 침공 (2022)":   ("2022-02-24", None),
    "이스라엘-하마스 전쟁 (2023)":     ("2023-10-07", None),
    "이란 공격 — 현재 (2026-02-28)":   ("2026-02-28", "🔴 진행 중: 데이터 제한적"),
}

SPX_TICKER   = "SPX INDEX:PX_LAST"
GOLD_TICKER  = "GC1 COMDTY:PX_LAST"
OIL_TICKER   = "WTI COMDTY:PX_LAST"
WINDOW       = 200
KOREAN_FONT  = r"C:\Windows\Fonts\malgun.ttf"

Figures = namedtuple("Figures", ["fig_main", "fig_mdd", "fig_bd", "fig_rv",
                                  "fig_gold", "fig_oil"])

COLOR_CURRENT = "#FF4B4B"
COLOR_COVID   = "#FFA500"
COLOR_GOLD    = "#FFD700"
COLOR_OIL     = "#F97316"

# ---------------------------------------------------------------------------
# Market commentary (user-provided, de-duplicated)
# ---------------------------------------------------------------------------
COMMENTARY = (
    "We believe that tomorrow risk-off assets like defensives, gold and treasuries "
    "would likely gain vs equities. Amidst EM equities, **India** remains vulnerable "
    "as a USD 10/bbl spike in oil worsens CAD by 0.4%–0.5% and raises inflation by "
    "0.3%–0.5%. **China** off late has built strategic reserves and **Brazil** actually "
    "gets helped by higher energy prices as it is an exporter. Asian peers such as "
    "**Taiwan** and **Korea** are also heavy oil importers and will be subjected to "
    "uncertainty. When prices hit a certain threshold (historically around USD 60–70), "
    "shale producers can ramp up drilling in months, not years — so the oil spike could "
    "be short-run. We suggest staying true to asset allocation for tomorrow as the war "
    "remains an evolving event and any news of de-escalation can bring flows back to "
    "risk assets, as has been seen in past geopolitical turmoil."
)

EM_OIL_IMPACT = {
    "인도 (취약)":         ("원유 순수입국 — $10/bbl 상승 시 CAD +0.4~0.5%, 인플레 +0.3~0.5%", "🔴"),
    "대만 (취약)":         ("원유 순수입국 — 에너지 비용 급등, 제조업 마진 압박", "🔴"),
    "한국 (취약)":         ("원유 순수입국 — 무역수지 악화, 원화 약세 압력", "🔴"),
    "중국 (완충)":         ("전략 비축유 보유 — 단기 충격 완화 가능, 중기 불확실성 존재", "🟡"),
    "브라질 (수혜)":       ("원유 순수출국 — 에너지 가격 상승이 무역수지·재정에 긍정적", "🟢"),
}


# ---------------------------------------------------------------------------
# 데이터 로딩
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="S&P 500 데이터 로딩 중…")
def load_spx() -> pd.Series:
    return Series(SPX_TICKER)


@st.cache_data(show_spinner="금(Gold) 데이터 로딩 중…")
def load_gold() -> pd.Series:
    return Series(GOLD_TICKER)


@st.cache_data(show_spinner="WTI 원유 데이터 로딩 중…")
def load_oil() -> pd.Series:
    return Series(OIL_TICKER)


# ---------------------------------------------------------------------------
# 분석 함수
# ---------------------------------------------------------------------------
def build_rebased(prices: pd.Series) -> dict[str, pd.Series]:
    result = {}
    for name, (start, _) in CONFLICTS.items():
        subset = prices.loc[start:].dropna().iloc[:WINDOW]
        if len(subset) < 2:
            continue
        rebased = subset / subset.iloc[0]
        result[name] = rebased.reset_index(drop=True)
    return result


def compute_stats(rebased: dict[str, pd.Series]) -> pd.DataFrame:
    """SPX-style stats: MDD, days-to-bottom, recovery-to-par, final return."""
    rows = []
    for name, s in rebased.items():
        start_date, note = CONFLICTS[name]
        days_avail = len(s)

        peak = s.cummax()
        drawdown = (s - peak) / peak
        mdd = drawdown.min()
        days_to_bottom = int(drawdown.idxmin())

        after_bottom = s.iloc[days_to_bottom:]
        recovered = after_bottom[after_bottom >= 1.0]
        recovery_days = (int(recovered.index[0]) - days_to_bottom
                         if len(recovered) > 0 else None)

        final_return = s.iloc[-1] - 1.0
        rows.append({
            "갈등": name,
            "시작일": start_date,
            "최대 낙폭": f"{mdd:.1%}",
            "저점 도달 (거래일)": str(days_to_bottom),
            "회복 소요일": str(recovery_days) if recovery_days is not None else "미회복",
            f"{days_avail}일 수익률": f"{final_return:+.1%}",
            "특이사항": note or "",
        })
    return pd.DataFrame(rows).set_index("갈등")


def compute_commodity_stats(rebased: dict[str, pd.Series]) -> pd.DataFrame:
    """Commodity-oriented stats: peak gain, days to peak, MDD, final return."""
    rows = []
    for name, s in rebased.items():
        start_date, note = CONFLICTS[name]
        days_avail = len(s)

        peak_gain = s.max() - 1.0
        days_to_peak = int(s.idxmax())

        cum_peak = s.cummax()
        drawdown = (s - cum_peak) / cum_peak
        mdd = drawdown.min()

        final_return = s.iloc[-1] - 1.0
        rows.append({
            "갈등": name,
            "시작일": start_date,
            "최대 상승": f"{peak_gain:+.1%}",
            "정점 도달 (거래일)": days_to_peak,
            "최대 낙폭 (정점比)": f"{mdd:.1%}",
            f"{days_avail}일 수익률": f"{final_return:+.1%}",
            "특이사항": note or "",
        })
    return pd.DataFrame(rows).set_index("갈등")


# ---------------------------------------------------------------------------
# Figure builder — called once, shared between display and PDF
# ---------------------------------------------------------------------------
def _conflict_line_chart(
    rebased: dict[str, pd.Series],
    title: str,
    highlight_color: str,
    yaxis_title: str = "리베이스 성과 (1.0 = 시작)",
) -> go.Figure:
    fig = go.Figure()
    for name, s in rebased.items():
        _, note = CONFLICTS[name]
        is_current = "현재" in name
        is_covid   = "2020" in name

        if is_current:
            line   = dict(width=3, color=COLOR_CURRENT, dash="dot")
            marker = dict(size=8, color=COLOR_CURRENT, symbol="star")
            mode   = "lines+markers"
        elif is_covid:
            line   = dict(width=2.5, color=COLOR_COVID, dash="dash")
            mode   = "lines"
            marker = {}
        else:
            line   = dict(width=1.5)
            mode   = "lines"
            marker = {}

        opacity = 1.0 if is_current else (0.85 if is_covid else 0.65)
        hover = f"거래일 %{{x}}<br>{name}: %{{y:.2%}}<extra></extra>"
        if note:
            hover = f"거래일 %{{x}}<br>{name}: %{{y:.2%}}<br>{note}<extra></extra>"

        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode=mode, name=name,
            line=line, marker=marker if marker else None,
            opacity=opacity, hovertemplate=hover,
        ))

    fig.add_hline(y=1.0, line_dash="dot", line_color="gray", line_width=1,
                  annotation_text="기준선 (1.0)", annotation_position="bottom right")
    fig.update_layout(
        height=500,
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="거래일 (갈등 발생 기준)",
        yaxis_title=yaxis_title,
        yaxis_tickformat=".0%",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left", font=dict(size=10)),
        margin=dict(l=50, r=220, t=50, b=60),
        hovermode="x unified",
    )
    return fig


def build_figures(
    spx_rebased: dict[str, pd.Series],
    gold_rebased: dict[str, pd.Series],
    oil_rebased: dict[str, pd.Series],
    stats_df: pd.DataFrame,
) -> Figures:
    # --- SPX ---
    fig_main = _conflict_line_chart(
        spx_rebased,
        title="S&P 500 — 갈등 발생 후 누적 성과",
        highlight_color=COLOR_CURRENT,
    )

    # --- Gold ---
    fig_gold = _conflict_line_chart(
        gold_rebased,
        title="금(Gold) — 갈등 발생 후 누적 성과",
        highlight_color=COLOR_GOLD,
        yaxis_title="리베이스 금 가격 (1.0 = 시작)",
    )

    # --- WTI ---
    fig_oil = _conflict_line_chart(
        oil_rebased,
        title="WTI 원유 — 갈등 발생 후 누적 성과",
        highlight_color=COLOR_OIL,
        yaxis_title="리베이스 WTI 가격 (1.0 = 시작)",
    )

    # --- SPX bar charts (historical only) ---
    historical = stats_df[~stats_df.index.str.contains("현재")].copy()

    mdd_vals = [float(historical.loc[i, "최대 낙폭"].replace("%", "")) / 100
                for i in historical.index]
    fig_mdd = go.Figure(go.Bar(
        x=list(historical.index), y=mdd_vals,
        marker_color=["#EF4444" if v < -0.1 else "#F97316" for v in mdd_vals],
        hovertemplate="%{x}<br>MDD: %{y:.1%}<extra></extra>",
    ))
    fig_mdd.update_layout(height=300, yaxis_tickformat=".0%", xaxis_tickangle=-45,
                          margin=dict(l=20, r=10, t=20, b=120), showlegend=False)

    bottom_days = [int(v) for v in historical["저점 도달 (거래일)"]]
    fig_bd = go.Figure(go.Bar(
        x=list(historical.index), y=bottom_days, marker_color="#6366F1",
        hovertemplate="%{x}<br>저점: %{y}일<extra></extra>",
    ))
    fig_bd.update_layout(height=300, xaxis_tickangle=-45,
                         margin=dict(l=20, r=10, t=20, b=120), showlegend=False)

    recovery_vals, recovery_labels = [], []
    for idx, row in historical.iterrows():
        r = row["회복 소요일"]
        if r == "미회복":
            recovery_vals.append(200)
            recovery_labels.append(f"{idx} (미회복)")
        else:
            recovery_vals.append(int(r))
            recovery_labels.append(idx)
    fig_rv = go.Figure(go.Bar(
        x=list(historical.index), y=recovery_vals,
        marker_color=["#9CA3AF" if "미회복" in l else "#10B981" for l in recovery_labels],
        hovertemplate="%{x}<br>회복: %{y}일<extra></extra>",
    ))
    fig_rv.update_layout(height=300, xaxis_tickangle=-45,
                         margin=dict(l=20, r=10, t=20, b=120), showlegend=False)

    return Figures(fig_main=fig_main, fig_mdd=fig_mdd, fig_bd=fig_bd, fig_rv=fig_rv,
                   fig_gold=fig_gold, fig_oil=fig_oil)


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------
def _fig_to_png(fig: go.Figure, width: int = 1100, height: int = 520) -> bytes:
    return pio.to_image(fig, format="png", width=width, height=height, scale=2)


def _write_chart_page(pdf: FPDF, fig: go.Figure, heading: str, set_font) -> None:
    pdf.add_page()
    set_font(bold=True, size=14)
    pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    png = _fig_to_png(fig)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(png)
        tmp_path = tmp.name
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.image(tmp_path, x=pdf.l_margin, w=usable_w)
    Path(tmp_path).unlink(missing_ok=True)


def _write_commodity_table(
    pdf: FPDF, df: pd.DataFrame, heading: str, set_font
) -> None:
    pdf.add_page()
    set_font(bold=True, size=14)
    pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Dynamic columns — skip 특이사항 for readability
    skip = {"특이사항"}
    cols = [c for c in df.columns if c not in skip]
    col_widths = {
        "시작일": 26, "최대 상승": 22, "정점 도달 (거래일)": 30,
        "최대 낙폭 (정점比)": 28,
    }
    # final return column has dynamic name
    for c in cols:
        if c not in col_widths:
            col_widths[c] = 28

    set_font(bold=True, size=8)
    pdf.set_fill_color(50, 80, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 7, "갈등", border=1, fill=True, align="C")
    for col in cols:
        pdf.cell(col_widths.get(col, 25), 7, col, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    set_font(size=7)
    for i, (idx, row) in enumerate(df.iterrows()):
        fill = i % 2 == 0
        pdf.set_fill_color(240, 250, 240) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(40, 6, str(idx)[:22], border=1, fill=fill, align="L")
        for col in cols:
            w = col_widths.get(col, 25)
            pdf.cell(w, 6, str(row.get(col, ""))[:20], border=1, fill=fill, align="C")
        pdf.ln()


def generate_pdf(
    figs: Figures,
    stats_df: pd.DataFrame,
    gold_stats: pd.DataFrame,
    oil_stats: pd.DataFrame,
    spx_rebased: dict[str, pd.Series],
    gold_rebased: dict[str, pd.Series],
    oil_rebased: dict[str, pd.Series],
) -> bytes:
    historical = stats_df[~stats_df.index.str.contains("현재")].copy()
    mdd_numeric      = [float(v.replace("%", "")) / 100 for v in historical["최대 낙폭"]]
    bottom_numeric   = [int(v) for v in historical["저점 도달 (거래일)"]]
    recovery_numeric = [int(v) for v in historical["회복 소요일"] if v != "미회복"]

    avg_mdd       = f"{np.mean(mdd_numeric):.1%}" if mdd_numeric else "N/A"
    avg_bottom    = f"{np.mean(bottom_numeric):.0f} 거래일" if bottom_numeric else "N/A"
    avg_recovery  = (f"{np.mean(recovery_numeric):.0f} 거래일"
                     if recovery_numeric else "N/A")
    recovery_rate = (f"{len(recovery_numeric) / len(historical):.0%}"
                     if historical.shape[0] else "N/A")

    current_name = "이란 공격 — 현재 (2026-02-28)"
    if current_name in spx_rebased:
        cs = spx_rebased[current_name]
        days_elapsed = len(cs)
        current_ret  = f"{cs.iloc[-1] - 1.0:+.1%}"
        current_low  = f"{cs.min() - 1:.1%}"
    else:
        days_elapsed, current_ret, current_low = 0, "N/A", "N/A"

    # Gold current
    gold_current_ret = "N/A"
    if current_name in gold_rebased:
        gc = gold_rebased[current_name]
        gold_current_ret = f"{gc.iloc[-1] - 1.0:+.1%}"

    # WTI current
    oil_current_ret = "N/A"
    if current_name in oil_rebased:
        oc = oil_rebased[current_name]
        oil_current_ret = f"{oc.iloc[-1] - 1.0:+.1%}"

    # Setup PDF
    pdf = FPDF()
    font_path = Path(KOREAN_FONT)
    use_korean = font_path.exists()
    if use_korean:
        pdf.add_font("Malgun", "",  str(font_path))
        pdf.add_font("Malgun", "B", str(font_path))

    def set_font(bold: bool = False, size: int = 11):
        if use_korean:
            pdf.set_font("Malgun", "B" if bold else "", size)
        else:
            pdf.set_font("Helvetica", "B" if bold else "", size)

    # ── Page 1: Title + Commentary + Iran metrics + SPX averages ─────────────
    pdf.add_page()
    set_font(bold=True, size=20)
    pdf.cell(0, 12, "전시 증시 분석: S&P 500 / 금 / WTI", new_x="LMARGIN",
             new_y="NEXT", align="C")
    set_font(size=11)
    pdf.cell(0, 8, "분석 기준일: 2026년 2월 28일", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Commentary box
    set_font(bold=True, size=11)
    pdf.cell(0, 8, "시장 분석 요약", new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(235, 242, 255)
    set_font(size=9)
    # Strip markdown bold markers for PDF
    commentary_plain = COMMENTARY.replace("**", "")
    pdf.multi_cell(0, 5.5, commentary_plain, border=1, fill=True)
    pdf.ln(4)

    # Iran metrics (3 assets)
    set_font(bold=True, size=12)
    pdf.cell(0, 8, "이란 공격 현황 (2026-02-28)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    col_w3 = (pdf.w - pdf.l_margin - pdf.r_margin) / 3
    asset_labels = ["S&P 500", "금 (Gold)", "WTI 원유"]
    asset_vals   = [current_ret, gold_current_ret, oil_current_ret]
    set_font(size=10)
    for label, value in zip(asset_labels, asset_vals):
        x0 = pdf.get_x()
        pdf.set_fill_color(240, 240, 245)
        pdf.multi_cell(col_w3 - 2, 7, f"{label}\n{value}", border=1, fill=True, align="C")
        pdf.set_xy(x0 + col_w3, pdf.get_y() - 14)
    pdf.ln(16)

    # SPX averages
    set_font(bold=True, size=12)
    pdf.cell(0, 8, "S&P 500 역사적 평균 (이란 현재 제외)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    col_w4 = (pdf.w - pdf.l_margin - pdf.r_margin) / 4
    set_font(size=10)
    for label, value in zip(
        ["평균 최대 낙폭", "평균 저점 도달", "평균 회복 소요일", "200일 내 회복률"],
        [avg_mdd, avg_bottom, avg_recovery, recovery_rate],
    ):
        x0 = pdf.get_x()
        pdf.set_fill_color(230, 245, 230)
        pdf.multi_cell(col_w4 - 2, 7, f"{label}\n{value}", border=1, fill=True, align="C")
        pdf.set_xy(x0 + col_w4, pdf.get_y() - 14)
    pdf.ln(16)

    # Scenarios
    set_font(bold=True, size=12)
    pdf.cell(0, 8, "낙관 시나리오", new_x="LMARGIN", new_y="NEXT")
    set_font(size=9)
    pdf.multi_cell(0, 5.5,
        "유사 선례: 이라크(2003), 코소보(1999), 걸프전(1990)\n"
        "예상 낙폭: -3%~-7%  |  회복: 30~60거래일  |  200일 후: +5%~+15%\n"
        "이란 공격이 단발성에 그치면 초기 충격 후 빠른 반등 가능성.")
    pdf.ln(3)
    set_font(bold=True, size=12)
    pdf.cell(0, 8, "비관 시나리오", new_x="LMARGIN", new_y="NEXT")
    set_font(size=9)
    pdf.multi_cell(0, 5.5,
        "유사 선례: 9/11(2001), 솔레이마니(2020)\n"
        "예상 낙폭: -10%~-25%+  |  회복: 100~200거래일 이상  |  200일 후: -5%~+5%\n"
        "중동 전면전 확대 또는 원유 공급 차질로 인플레이션 재점화 시 중장기 하방 압력.")
    pdf.ln(3)
    set_font(bold=True, size=11)
    pdf.cell(0, 7, "COVID-19 왜곡 경고 (2020)", new_x="LMARGIN", new_y="NEXT")
    set_font(size=9)
    pdf.multi_cell(0, 5.5,
        "2020년 솔레이마니 공습 이후 COVID-19 팬데믹과 겹쳐 S&P 500이 -34% 급락. "
        "순수 지정학적 충격이 아닌 블랙스완 중첩으로 해석해야 하며 단순 비교는 주의 요망.")

    # ── Page 2: SPX chart ─────────────────────────────────────────────────────
    _write_chart_page(pdf, figs.fig_main, "S&P 500 — 갈등 발생 후 누적 성과", set_font)

    # ── Page 3: Gold chart ────────────────────────────────────────────────────
    _write_chart_page(pdf, figs.fig_gold, "금(Gold) — 갈등 발생 후 누적 성과", set_font)

    # ── Page 4: WTI chart ─────────────────────────────────────────────────────
    _write_chart_page(pdf, figs.fig_oil, "WTI 원유 — 갈등 발생 후 누적 성과", set_font)

    # ── Page 5: Gold + WTI commodity stats ───────────────────────────────────
    _write_commodity_table(pdf, gold_stats, "금(Gold) 갈등별 통계", set_font)
    _write_commodity_table(pdf, oil_stats,  "WTI 원유 갈등별 통계", set_font)

    # ── Page 7: SPX stats table ───────────────────────────────────────────────
    pdf.add_page()
    set_font(bold=True, size=14)
    pdf.cell(0, 10, "S&P 500 갈등별 시장 반응 통계", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    spx_cols   = ["시작일", "최대 낙폭", "저점 도달 (거래일)", "회복 소요일", "특이사항"]
    spx_widths = [28, 22, 32, 22, 55]
    set_font(bold=True, size=8)
    pdf.set_fill_color(50, 50, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 7, "갈등", border=1, fill=True, align="C")
    for col, w in zip(spx_cols, spx_widths):
        pdf.cell(w, 7, col, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    set_font(size=7)
    for i, (idx, row) in enumerate(stats_df.iterrows()):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(40, 6, str(idx)[:22], border=1, fill=fill, align="L")
        for col, w in zip(spx_cols, spx_widths):
            val = str(row.get(col, ""))
            if col == "특이사항" and val[:2] in ("⚠️", "🔴"):
                val = val[2:].strip()
            pdf.cell(w, 6, val[:28], border=1, fill=fill, align="C")
        pdf.ln()

    # ── Page 8: SPX bar charts ────────────────────────────────────────────────
    pdf.add_page()
    set_font(bold=True, size=14)
    pdf.cell(0, 10, "S&P 500 갈등별 통계 분포", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    chart_w = (pdf.w - pdf.l_margin - pdf.r_margin - 6) / 3
    chart_h = chart_w * 0.85
    for fig, title in [
        (figs.fig_mdd, "최대 낙폭 분포"),
        (figs.fig_bd,  "저점 도달 거래일"),
        (figs.fig_rv,  "저점 이후 회복 소요일"),
    ]:
        png = pio.to_image(fig, format="png", width=500, height=400, scale=2)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png)
            tmp_path = tmp.name
        x0, y0 = pdf.get_x(), pdf.get_y()
        set_font(bold=True, size=9)
        pdf.cell(chart_w, 6, title, align="C")
        pdf.set_xy(x0, y0 + 7)
        pdf.image(tmp_path, x=pdf.get_x(), w=chart_w, h=chart_h)
        pdf.set_xy(x0 + chart_w + 3, y0)
        Path(tmp_path).unlink(missing_ok=True)

    # ── Page 9: Monitoring table ──────────────────────────────────────────────
    pdf.add_page()
    set_font(bold=True, size=14)
    pdf.cell(0, 10, "핵심 모니터링 지표", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    monitoring = [
        ("원유 (WTI/Brent)", "$90 이하 유지", "$100 돌파 및 유지"),
        ("VIX (변동성 지수)", "20 이하 빠른 하락", "30 이상 지속"),
        ("달러 인덱스 (DXY)", "안정 또는 약달러", "급등 (위험회피 심화)"),
        ("이란 확전 여부", "단발성 공격 종결", "호르무즈 해협 봉쇄 위협"),
        ("미국 연준 반응", "통화 완화 신호", "인플레 우려로 금리 동결"),
        ("이스라엘/중동 연계", "충돌 범위 제한", "중동 전면전 확대"),
    ]
    set_font(bold=True, size=9)
    pdf.set_fill_color(50, 50, 80)
    pdf.set_text_color(255, 255, 255)
    for label, w in [("지표", 55), ("낙관 신호", 65), ("비관 신호", 65)]:
        pdf.cell(w, 7, label, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    set_font(size=8)
    for i, (metric, bull, bear) in enumerate(monitoring):
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(55, 6, metric, border=1, fill=fill)
        pdf.set_fill_color(230, 245, 230) if fill else pdf.set_fill_color(240, 255, 240)
        pdf.cell(65, 6, bull, border=1, fill=fill)
        pdf.set_fill_color(255, 235, 235) if fill else pdf.set_fill_color(255, 240, 240)
        pdf.cell(65, 6, bear, border=1, fill=fill)
        pdf.ln()

    pdf.ln(5)
    set_font(bold=True, size=12)
    pdf.cell(0, 8, "EM 원유 충격 영향 분석", new_x="LMARGIN", new_y="NEXT")
    set_font(size=8)
    for country, (desc, _) in EM_OIL_IMPACT.items():
        pdf.cell(45, 6, country, border=1)
        pdf.cell(0, 6, desc, border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    set_font(size=8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5,
        "본 분석은 역사적 선례에 기반한 참고 자료이며, 투자 조언이 아닙니다. "
        "2026년 2월 28일 기준 진행 중인 사건으로 상황은 빠르게 변화할 수 있습니다.")

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# 메인 앱
# ---------------------------------------------------------------------------
def main():
    st.title("⚔️ 전시 증시 분석: S&P 500 / 금 / WTI")

    # --- 데이터 로드 ---
    try:
        spx  = load_spx()
        gold = load_gold()
        oil  = load_oil()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

    spx_rebased  = build_rebased(spx)
    gold_rebased = build_rebased(gold)
    oil_rebased  = build_rebased(oil)

    if not spx_rebased:
        st.warning("리베이스 데이터를 생성할 수 없습니다.")
        st.stop()

    stats_df   = compute_stats(spx_rebased)
    gold_stats = compute_commodity_stats(gold_rebased)
    oil_stats  = compute_commodity_stats(oil_rebased)
    figs       = build_figures(spx_rebased, gold_rebased, oil_rebased, stats_df)

    historical       = stats_df[~stats_df.index.str.contains("현재")].copy()
    mdd_numeric      = [float(v.replace("%", "")) / 100 for v in historical["최대 낙폭"]]
    bottom_numeric   = [int(v) for v in historical["저점 도달 (거래일)"]]
    recovery_numeric = [int(v) for v in historical["회복 소요일"] if v != "미회복"]

    # ── Header row + PDF button ───────────────────────────────────────────────
    header_col, btn_col = st.columns([5, 1])
    with header_col:
        st.caption(
            "지정학적 갈등 발생 시점부터 200거래일 간 S&P 500 / 금 / WTI 반응을 분석하고, "
            "2026년 2월 28일 이란 공격에 대한 시사점을 도출합니다."
        )
    with btn_col:
        if st.button("📥 PDF 다운로드", use_container_width=True):
            with st.spinner("PDF 생성 중..."):
                st.session_state["pdf_bytes"] = generate_pdf(
                    figs, stats_df, gold_stats, oil_stats,
                    spx_rebased, gold_rebased, oil_rebased,
                )

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            "⬇ 저장",
            data=st.session_state["pdf_bytes"],
            file_name="전시_증시_분석.pdf",
            mime="application/pdf",
        )

    # ── Market commentary ─────────────────────────────────────────────────────
    st.info(COMMENTARY, icon="📋")

    # =========================================================================
    # Section 1 — S&P 500 성과 차트
    # =========================================================================
    st.divider()
    st.subheader("📈 S&P 500 — 갈등 발생 후 누적 성과 (리베이스 = 1.0)")

    highlight_current = st.toggle("이란 공격(현재) 강조 표시", value=True, key="highlight")
    for trace in figs.fig_main.data:
        is_current = "현재" in trace.name
        is_covid   = "2020" in trace.name
        if is_current:
            trace.opacity = 1.0 if highlight_current else 0.4
        elif is_covid:
            trace.opacity = 0.85
        else:
            trace.opacity = 0.65 if highlight_current else 0.85

    st.plotly_chart(figs.fig_main, use_container_width=True)
    st.caption("* 2020년 솔레이마니 공습은 이후 COVID-19 팬데믹과 겹쳐 시장 급락이 발생했습니다.")

    # =========================================================================
    # Section 2 — SPX 통계 테이블
    # =========================================================================
    st.divider()
    st.subheader("📊 S&P 500 갈등별 시장 반응 통계")
    st.dataframe(stats_df, use_container_width=True)

    # =========================================================================
    # Section 3 — SPX 막대 차트 3종
    # =========================================================================
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**최대 낙폭 분포**")
        st.plotly_chart(figs.fig_mdd, use_container_width=True)
    with col2:
        st.markdown("**저점 도달 거래일**")
        st.plotly_chart(figs.fig_bd, use_container_width=True)
    with col3:
        st.markdown("**저점 이후 회복 소요일**")
        st.plotly_chart(figs.fig_rv, use_container_width=True)

    # =========================================================================
    # Section 4 — SPX 요약 지표 카드
    # =========================================================================
    st.divider()
    st.subheader("S&P 500 역사적 평균 (이란 현재 제외)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("평균 최대 낙폭",    f"{np.mean(mdd_numeric):.1%}")
    m2.metric("평균 저점 도달",    f"{np.mean(bottom_numeric):.0f} 거래일")
    m3.metric("평균 회복 소요일",
              f"{np.mean(recovery_numeric):.0f} 거래일" if recovery_numeric else "N/A")
    m4.metric("200일 내 회복률",   f"{len(recovery_numeric) / len(historical):.0%}")

    # =========================================================================
    # Section 5 — 금(Gold) 성과
    # =========================================================================
    st.divider()
    st.subheader("🥇 금(Gold) — 갈등 발생 후 누적 성과 (안전자산)")

    col_g1, col_g2 = st.columns([3, 1], gap="large")
    with col_g1:
        st.plotly_chart(figs.fig_gold, use_container_width=True)
    with col_g2:
        st.caption("**과거 갈등 시 금 평균 동향**")
        if gold_rebased:
            hist_gold = {k: v for k, v in gold_rebased.items() if "현재" not in k}
            peak_gains = [s.max() - 1.0 for s in hist_gold.values()]
            final_rets = [s.iloc[-1] - 1.0 for s in hist_gold.values()]
            st.metric("평균 최대 상승", f"{np.mean(peak_gains):+.1%}")
            st.metric("평균 200일 수익률", f"{np.mean(final_rets):+.1%}")
            pos_count = sum(1 for r in final_rets if r > 0)
            st.metric("200일 후 플러스 비율", f"{pos_count / len(final_rets):.0%}")

        # Current gold
        current_name = "이란 공격 — 현재 (2026-02-28)"
        if current_name in gold_rebased:
            gc = gold_rebased[current_name]
            st.divider()
            st.metric("현재 금 누적 수익률", f"{gc.iloc[-1] - 1.0:+.1%}")

    st.dataframe(gold_stats, use_container_width=True)
    st.caption(
        "금은 지정학적 갈등 시 전형적인 안전자산 수요 증가로 단기 상승하는 경향이 있습니다. "
        "\"최대 낙폭\"은 정점 이후 가격이 얼마나 반납했는지를 나타냅니다."
    )

    # =========================================================================
    # Section 6 — WTI 원유 성과
    # =========================================================================
    st.divider()
    st.subheader("🛢️ WTI 원유 — 갈등 발생 후 누적 성과")

    col_o1, col_o2 = st.columns([3, 1], gap="large")
    with col_o1:
        st.plotly_chart(figs.fig_oil, use_container_width=True)
    with col_o2:
        st.caption("**과거 갈등 시 WTI 평균 동향**")
        if oil_rebased:
            hist_oil = {k: v for k, v in oil_rebased.items() if "현재" not in k}
            oil_peaks  = [s.max() - 1.0 for s in hist_oil.values()]
            oil_finals = [s.iloc[-1] - 1.0 for s in hist_oil.values()]
            st.metric("평균 최대 스파이크", f"{np.mean(oil_peaks):+.1%}")
            st.metric("평균 200일 수익률",  f"{np.mean(oil_finals):+.1%}")

        if current_name in oil_rebased:
            oc = oil_rebased[current_name]
            st.divider()
            st.metric("현재 WTI 누적 수익률", f"{oc.iloc[-1] - 1.0:+.1%}")

    st.dataframe(oil_stats, use_container_width=True)

    # Shale supply response note
    st.info(
        "**셰일 공급 반응 완충**: WTI가 USD 60–70/bbl 수준에 도달하면 미국 셰일 생산자들이 "
        "수개월 내 생산을 증대할 수 있어 유가 스파이크가 단기에 그칠 가능성이 있습니다.",
        icon="⚡",
    )

    # EM Oil Impact Table
    st.divider()
    st.subheader("🌏 원유 가격 충격의 EM 국가별 영향")
    st.caption("USD 10/bbl 상승 기준 추정 영향")

    em_rows = []
    for country, (desc, emoji) in EM_OIL_IMPACT.items():
        em_rows.append({"국가": f"{emoji} {country}", "영향 및 근거": desc})
    st.table(pd.DataFrame(em_rows).set_index("국가"))

    # =========================================================================
    # Section 7 — 이란 현재 현황
    # =========================================================================
    st.divider()
    st.subheader("🔴 이란 공격 (2026년 2월 28일) — 현황")

    if current_name in spx_rebased:
        cs   = spx_rebased[current_name]
        gc   = gold_rebased.get(current_name)
        oc   = oil_rebased.get(current_name)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("경과 거래일",         f"{len(cs)}일")
        c2.metric("S&P 500 수익률",      f"{cs.iloc[-1] - 1.0:+.1%}")
        c3.metric("S&P 500 저점",        f"{cs.min() - 1:.1%}")
        c4.metric("금 수익률",           f"{gc.iloc[-1] - 1.0:+.1%}" if gc is not None else "N/A")
        c5.metric("WTI 수익률",          f"{oc.iloc[-1] - 1.0:+.1%}" if oc is not None else "N/A")
    else:
        st.warning("이란 공격 데이터가 아직 없거나 로드되지 않았습니다.")

    # =========================================================================
    # Section 8 — 시나리오
    # =========================================================================
    st.divider()
    st.subheader("📌 역사적 선례 기반 시나리오")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
### 낙관 시나리오 (빠른 회복)
**유사 선례**: 이라크 전쟁(2003), 코소보(1999), 걸프전(1990)

- 지정학적 충격이 단기(1~4주) 내 흡수
- **예상 낙폭**: -3% ~ -7%
- **회복 예상**: 30~60 거래일 이내
- **200일 후 예상**: +5% ~ +15%

**근거**
> 이란 공격이 단발성 군사 행동에 그치고 확전이 제한될 경우,
> 과거 사례처럼 초기 충격 후 빠른 반등이 나타날 가능성이 높습니다.
""")

    with col_b:
        st.markdown("""
### 비관 시나리오 (장기 충격)
**유사 선례**: 9/11(2001), 솔레이마니(2020)*

- 지정학적 불확실성 장기화 또는 추가 악재 중첩
- **예상 낙폭**: -10% ~ -25%+
- **회복 예상**: 100~200 거래일 이상
- **200일 후 예상**: -5% ~ +5%

**근거**
> 이란 공격이 중동 전면전으로 확대되거나, 원유 공급 차질로
> 인플레이션이 재점화될 경우 중장기 하방 압력이 증가합니다.
""")

    # =========================================================================
    # Section 9 — COVID 경고
    # =========================================================================
    st.divider()
    st.subheader("⚠️ 2020년 솔레이마니 공습 사례의 교훈")
    st.warning("""
**COVID-19 동시 발생에 의한 왜곡**

2020년 1월 3일 솔레이마니 이란 혁명수비대 사령관 제거 작전 직후,
S&P 500은 단기 조정 후 회복세를 보였으나, 이후 **2020년 2월~3월 COVID-19
팬데믹 충격**과 겹쳐 -34% 급락이 발생했습니다.

이는 순수한 지정학적 충격이 아닌, **독립적 블랙스완(팬데믹)과의 중첩**으로
해석해야 하며, 현재 이란 공격 분석 시 단순 비교는 주의가 필요합니다.

> 핵심 교훈: 지정학적 충격 자체보다 **거시 환경(인플레이션, 연준 정책, 경제 사이클)**
> 이 시장의 회복 속도를 결정짓는 더 중요한 변수입니다.
    """, icon="⚠️")

    # =========================================================================
    # Section 10 — 모니터링 테이블
    # =========================================================================
    st.divider()
    st.subheader("🗺️ 핵심 모니터링 지표")
    st.markdown("""
| 지표 | 낙관 신호 | 비관 신호 |
|------|----------|----------|
| **원유(WTI/Brent)** | $90 이하 유지 | $100 돌파 및 유지 |
| **VIX (변동성 지수)** | 20 이하 빠른 하락 | 30 이상 지속 |
| **달러 인덱스(DXY)** | 안정 또는 약달러 | 급등 (위험회피 심화) |
| **이란 확전 여부** | 단발성 공격 종결 | 호르무즈 해협 봉쇄 위협 |
| **미국 연준 반응** | 통화 완화 신호 | 인플레 우려로 금리 동결 |
| **이스라엘/중동 연계** | 충돌 범위 제한 | 중동 전면전 확대 |
    """)

    st.caption(
        "본 분석은 역사적 선례에 기반한 참고 자료이며, 투자 조언이 아닙니다. "
        "2026년 2월 28일 기준 진행 중인 사건으로 상황은 빠르게 변화할 수 있습니다."
    )


if __name__ == "__main__":
    main()
