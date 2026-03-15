"""Quantitative analytics API endpoints.

Returns Plotly figure JSON for correlation, regression, PCA, and VaR analysis.
"""

from __future__ import annotations

import json
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from fastapi import APIRouter, Depends, HTTPException, Query

from ix.api.dependencies import get_current_user
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import dendrogram

from ix.db.query import Series
from ix.core.quantitative import (
    correlation_matrix,
    rolling_correlation,
    hierarchical_cluster,
    rolling_beta,
    multi_factor_regression,
    pca_decomposition,
    historical_var,
    parametric_var,
    expected_shortfall,
    rolling_var,
)
from ix.misc import get_logger

router = APIRouter()
logger = get_logger(__name__)

# ── Palette ──────────────────────────────────────────────────────────────────
_PALETTE = [
    "#38bdf8", "#f59e0b", "#a78bfa", "#34d399", "#fb7185",
    "#60a5fa", "#facc15", "#c084fc", "#4ade80", "#f87171",
]


def _codes_to_df(codes_csv: str) -> pd.DataFrame:
    """Parse comma-separated codes into a price DataFrame via Series()."""
    codes = [c.strip() for c in codes_csv.split(",") if c.strip()]
    if len(codes) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 comma-separated series codes.")
    df = pd.DataFrame({c: Series(c) for c in codes}).dropna()
    if df.empty:
        raise HTTPException(status_code=404, detail="No overlapping data for the provided codes.")
    return df


def _short_name(code: str) -> str:
    """Shorten a Bloomberg-style code for display."""
    return code.split(":")[0].strip()


# ── Correlation ──────────────────────────────────────────────────────────────

@router.get("/quant/correlation/matrix")
def quant_correlation_matrix(
    codes: str = Query(..., description="Comma-separated series codes"),
    window: Optional[int] = Query(None, ge=20, description="Trailing window (observations)"),
    method: str = Query("pearson", description="pearson | spearman | kendall"),
    _user=Depends(get_current_user),
):
    """Heatmap correlation matrix with hierarchical clustering dendrogram."""
    try:
        df = _codes_to_df(codes)
        df.columns = [_short_name(c) for c in df.columns]

        corr = correlation_matrix(df, window=window, method=method)
        cluster = hierarchical_cluster(corr)

        # Reorder by dendrogram leaves
        dendro = dendrogram(cluster["linkage"], labels=cluster["labels"], no_plot=True)
        order = dendro["leaves"]
        labels_ordered = [cluster["labels"][i] for i in order]
        corr_ordered = corr.loc[labels_ordered, labels_ordered]

        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.78, 0.22],
            subplot_titles=["Correlation Matrix", "Cluster Dendrogram"],
            horizontal_spacing=0.08,
        )

        # Heatmap
        fig.add_trace(
            go.Heatmap(
                z=corr_ordered.values,
                x=corr_ordered.columns.tolist(),
                y=corr_ordered.index.tolist(),
                colorscale="RdBu_r",
                zmin=-1, zmax=1,
                text=corr_ordered.values.round(2),
                texttemplate="%{text}",
                textfont=dict(size=10),
                colorbar=dict(len=0.6, x=0.72, thickness=12),
            ),
            row=1, col=1,
        )

        # Dendrogram (horizontal, drawn manually)
        icoord = dendro["icoord"]
        dcoord = dendro["dcoord"]
        for xs, ys in zip(icoord, dcoord):
            fig.add_trace(
                go.Scatter(
                    x=ys, y=xs,
                    mode="lines",
                    line=dict(color="#64748b", width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1, col=2,
            )

        fig.update_layout(
            height=max(420, 60 * len(labels_ordered)),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        fig.update_xaxes(showticklabels=False, row=1, col=2)
        fig.update_yaxes(showticklabels=False, row=1, col=2)

        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_correlation_matrix failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quant/correlation/rolling")
def quant_rolling_correlation(
    code1: str = Query(...),
    code2: str = Query(...),
    window: int = Query(60, ge=10, le=504),
    _user=Depends(get_current_user),
):
    """Rolling correlation line chart between two series."""
    try:
        s1 = Series(code1)
        s2 = Series(code2)
        if s1.empty or s2.empty:
            raise HTTPException(status_code=404, detail="One or both series not found.")

        rc = rolling_correlation(s1, s2, window=window).dropna()
        if rc.empty:
            raise HTTPException(
                status_code=400,
                detail="Not enough overlapping return data to compute rolling correlation.",
            )

        n1, n2 = _short_name(code1), _short_name(code2)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rc.index, y=rc.values,
            mode="lines", name=f"Corr({n1}, {n2})",
            line=dict(color="#38bdf8", width=1.5),
        ))
        fig.add_hline(y=0, line_dash="dot", line_color="#64748b", opacity=0.5)
        fig.update_layout(
            title=f"Rolling {window}d Correlation: {n1} vs {n2}",
            yaxis_title="Correlation",
            height=420,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_rolling_correlation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Regression ───────────────────────────────────────────────────────────────

@router.get("/quant/regression/ols")
def quant_ols_regression(
    y: str = Query(..., description="Dependent series code"),
    x: str = Query(..., description="Comma-separated factor codes"),
    _user=Depends(get_current_user),
):
    """4-panel OLS regression: scatter/fitted, residuals, histogram, stats."""
    try:
        x_codes = [c.strip() for c in x.split(",") if c.strip()]
        if not x_codes:
            raise HTTPException(status_code=400, detail="Provide at least one factor code in 'x'.")

        y_series = Series(y)
        factors = pd.DataFrame({c: Series(c) for c in x_codes}).dropna()
        if y_series.empty or factors.empty:
            raise HTTPException(status_code=404, detail="Series not found.")

        result = multi_factor_regression(y_series, factors)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                "Fitted vs Actual", "Residuals",
                "Residual Distribution", "Regression Stats",
            ],
            vertical_spacing=0.14,
            horizontal_spacing=0.10,
        )

        # 1. Fitted vs Actual
        fig.add_trace(go.Scatter(
            x=result["fitted"].index, y=result["fitted"].values,
            mode="lines", name="Fitted", line=dict(color="#f59e0b", width=1.5),
        ), row=1, col=1)

        y_ret = y_series.pct_change().dropna()
        y_aligned = y_ret.reindex(result["fitted"].index)
        fig.add_trace(go.Scatter(
            x=y_aligned.index, y=y_aligned.values,
            mode="lines", name="Actual", line=dict(color="#38bdf8", width=1),
            opacity=0.6,
        ), row=1, col=1)

        # 2. Residuals
        fig.add_trace(go.Scatter(
            x=result["residuals"].index, y=result["residuals"].values,
            mode="lines", name="Residuals", line=dict(color="#a78bfa", width=1),
        ), row=1, col=2)
        fig.add_hline(y=0, line_dash="dot", line_color="#64748b", opacity=0.5, row=1, col=2)

        # 3. Residual histogram
        fig.add_trace(go.Histogram(
            x=result["residuals"].values,
            nbinsx=40, name="Residuals",
            marker_color="#34d399", opacity=0.75,
        ), row=2, col=1)

        # 4. Stats table
        y_name = _short_name(y)
        coef_lines = [f"<b>{_short_name(k)}</b>: {v:.4f} (p={result['p_values'].get(k, float('nan')):.3f})"
                      for k, v in result["coefficients"].items()]
        stats_text = (
            f"<b>Dependent:</b> {y_name}<br>"
            f"<b>R²:</b> {result['r_squared']:.4f}<br>"
            f"<b>Intercept:</b> {result['intercept']:.6f} "
            f"(p={result['p_values']['intercept']:.3f})<br><br>"
            + "<br>".join(coef_lines)
        )
        fig.add_trace(go.Scatter(
            x=[0.5], y=[0.5],
            mode="text",
            text=[stats_text],
            textfont=dict(size=11),
            showlegend=False,
            hoverinfo="skip",
        ), row=2, col=2)
        fig.update_xaxes(visible=False, row=2, col=2)
        fig.update_yaxes(visible=False, row=2, col=2)

        fig.update_layout(
            height=600,
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False,
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_ols_regression failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quant/regression/rolling-beta")
def quant_rolling_beta(
    y: str = Query(...),
    x: str = Query(...),
    window: int = Query(60, ge=10, le=504),
    _user=Depends(get_current_user),
):
    """Rolling beta line chart with beta=1 reference."""
    try:
        s_y = Series(y)
        s_x = Series(x)
        if s_y.empty or s_x.empty:
            raise HTTPException(status_code=404, detail="Series not found.")

        beta = rolling_beta(s_y, s_x, window=window).dropna()
        if beta.empty:
            raise HTTPException(
                status_code=400,
                detail="Not enough overlapping return data to compute rolling beta.",
            )
        yn, xn = _short_name(y), _short_name(x)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=beta.index, y=beta.values,
            mode="lines", name=f"β({yn}/{xn})",
            line=dict(color="#38bdf8", width=1.5),
        ))
        fig.add_hline(y=1, line_dash="dot", line_color="#f59e0b", opacity=0.6,
                       annotation_text="β=1")
        fig.add_hline(y=0, line_dash="dot", line_color="#64748b", opacity=0.3)
        fig.update_layout(
            title=f"Rolling {window}d Beta: {yn} vs {xn}",
            yaxis_title="Beta",
            height=420,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_rolling_beta failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── PCA ──────────────────────────────────────────────────────────────────────

@router.get("/quant/pca")
def quant_pca(
    codes: str = Query(..., description="Comma-separated series codes"),
    n_components: int = Query(3, ge=1, le=10),
    _user=Depends(get_current_user),
):
    """3-panel PCA: scree bar, loadings heatmap, component time series."""
    try:
        df = _codes_to_df(codes)
        df.columns = [_short_name(c) for c in df.columns]

        result = pca_decomposition(df, n_components=n_components)
        n = len(result["explained_variance_ratio"])
        comp_names = [f"PC{i+1}" for i in range(n)]

        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{}, {}], [{"colspan": 2}, None]],
            subplot_titles=[
                "Explained Variance",
                "Factor Loadings",
                "Principal Components Over Time",
            ],
            vertical_spacing=0.14,
            horizontal_spacing=0.10,
        )

        # 1. Scree bar
        fig.add_trace(go.Bar(
            x=comp_names,
            y=[v * 100 for v in result["explained_variance_ratio"]],
            marker_color="#38bdf8",
            name="Variance %",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=comp_names,
            y=[v * 100 for v in result["cumulative_variance"]],
            mode="lines+markers",
            name="Cumulative %",
            line=dict(color="#f59e0b", width=2),
            marker=dict(size=6),
        ), row=1, col=1)
        fig.update_yaxes(title_text="%", row=1, col=1)

        # 2. Loadings heatmap
        loadings = result["loadings"]
        fig.add_trace(go.Heatmap(
            z=loadings.values,
            x=loadings.columns.tolist(),
            y=loadings.index.tolist(),
            colorscale="RdBu_r",
            text=loadings.values.round(2),
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorbar=dict(len=0.4, y=0.78, thickness=12),
        ), row=1, col=2)

        # 3. Component time series
        components = result["components"]
        for i, col in enumerate(components.columns):
            fig.add_trace(go.Scatter(
                x=components.index, y=components[col],
                mode="lines", name=col,
                line=dict(color=_PALETTE[i % len(_PALETTE)], width=1.2),
            ), row=2, col=1)

        fig.update_layout(
            height=650,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_pca failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── VaR ──────────────────────────────────────────────────────────────────────

@router.get("/quant/var")
def quant_var(
    code: str = Query(...),
    confidence: float = Query(0.95, ge=0.9, le=0.999),
    window: Optional[int] = Query(None, ge=20),
    method: str = Query("historical", description="historical | parametric"),
    _user=Depends(get_current_user),
):
    """Return distribution histogram with VaR and CVaR lines."""
    try:
        s = Series(code)
        if s.empty:
            raise HTTPException(status_code=404, detail="Series not found.")

        es_result = expected_shortfall(s, confidence=confidence, window=window)
        if method == "parametric":
            var_result = parametric_var(s, confidence=confidence, window=window)
        else:
            var_result = historical_var(s, confidence=confidence, window=window)

        returns = es_result["returns"]
        var_val = var_result["var"]
        es_val = es_result["es"]
        if returns.empty or not np.isfinite(var_val) or not np.isfinite(es_val):
            raise HTTPException(
                status_code=400,
                detail="Not enough clean return history to compute VaR/CVaR.",
            )

        name = _short_name(code)
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=returns.values,
            nbinsx=80,
            name="Returns",
            marker_color="#38bdf8",
            opacity=0.7,
        ))
        fig.add_vline(x=-var_val, line_dash="dash", line_color="#f59e0b", line_width=2,
                       annotation_text=f"VaR {confidence:.0%}: {-var_val:.4f}",
                       annotation_position="top left")
        fig.add_vline(x=-es_val, line_dash="dash", line_color="#fb7185", line_width=2,
                       annotation_text=f"CVaR: {-es_val:.4f}",
                       annotation_position="top left")
        fig.update_layout(
            title=f"{name} Return Distribution — {method.title()} VaR ({confidence:.0%})",
            xaxis_title="Daily Return",
            yaxis_title="Frequency",
            height=420,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_var failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quant/var/rolling")
def quant_rolling_var(
    code: str = Query(...),
    confidence: float = Query(0.95, ge=0.9, le=0.999),
    window: int = Query(252, ge=20, le=756),
    _user=Depends(get_current_user),
):
    """Rolling VaR line + price on secondary axis."""
    try:
        s = Series(code)
        if s.empty:
            raise HTTPException(status_code=404, detail="Series not found.")

        rvar = rolling_var(s, confidence=confidence, window=window).dropna()
        if rvar.empty:
            raise HTTPException(
                status_code=400,
                detail="Not enough clean return history to compute rolling VaR.",
            )
        price = s.reindex(rvar.index)
        name = _short_name(code)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Scatter(
            x=price.index, y=price.values,
            mode="lines", name=name,
            line=dict(color="#64748b", width=1),
            opacity=0.5,
        ), secondary_y=True)

        fig.add_trace(go.Scatter(
            x=rvar.index, y=rvar.values,
            mode="lines", name=f"VaR {confidence:.0%}",
            line=dict(color="#fb7185", width=1.5),
        ), secondary_y=False)

        fig.update_layout(
            title=f"Rolling {window}d VaR ({confidence:.0%}): {name}",
            height=420,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        fig.update_yaxes(title_text="VaR (loss)", secondary_y=False)
        fig.update_yaxes(title_text="Price", secondary_y=True)

        return json.loads(pio.to_json(fig, engine="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quant_rolling_var failed")
        raise HTTPException(status_code=500, detail="Internal server error")
