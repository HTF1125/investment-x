"""Convert ChartPack series-based charts to Custom Charts with full Python code.

Takes chartpack configs (code + series JSON) and generates standalone Python
code that produces a complete Plotly figure.
"""
import os, sys, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ix.db.conn import conn
conn.connect()

from sqlalchemy.orm import Session
from ix.db.models.chart_pack import ChartPack
from ix.db.models import Charts, User
from datetime import datetime, timezone

YOUR_ID = "096862b7-b643-40a5-9f58-e41a39520fc0"


def generate_custom_code(config: dict) -> str:
    """Convert a chartpack config into standalone Custom Chart Python code."""
    code = config.get("code", "").strip()
    series = config.get("series", [])
    title = config.get("title", "")
    panes = config.get("panes", [{"id": 0, "label": ""}])
    show_legend = config.get("showLegend", True)
    legend_pos = config.get("legendPosition", "top")
    show_recessions = config.get("showRecessions", False)
    show_gridlines = config.get("showGridlines", True)
    active_range = config.get("activeRange", "MAX")

    if not code or not series:
        return ""

    # Determine if multi-pane
    pane_ids = sorted(set(s.get("yAxisIndex", 0) for s in series))
    n_panes = max(len(panes), max(pane_ids) + 1) if pane_ids else 1

    # Build the Python code
    lines = []
    lines.append("# Data")
    lines.append(code)
    lines.append("")

    # Handle the data variable name - could be 'result' or assigned in code
    # The pack code typically does: result = MultiSeries({...}) or result = Series(...)
    data_var = "result"

    if n_panes > 1:
        lines.append(f"fig = make_subplots(rows={n_panes}, cols=1, shared_xaxes=True,")
        lines.append(f"    vertical_spacing=0.03,")
        row_heights = [1.0 / n_panes] * n_panes
        lines.append(f"    row_heights={row_heights})")
    else:
        lines.append("fig = go.Figure()")

    lines.append("")

    # Convert series to traces
    for i, s in enumerate(series):
        s_code = s.get("code", "")  # Column name in the DataFrame
        s_name = s.get("name", s_code)
        chart_type = s.get("chartType", "line")
        visible = s.get("visible", True)
        y_axis_idx = s.get("yAxisIndex", 0)
        transform = s.get("transform", "none")
        color = s.get("color", "")

        if not s_code:
            continue

        # Data access
        data_expr = f'{data_var}["{s_code}"]'

        # Apply transform
        if transform == "pctChange":
            data_expr = f"{data_expr}.pct_change() * 100"
        elif transform == "yoy":
            data_expr = f"{data_expr}.pct_change(12) * 100"
        elif transform == "rebase":
            data_expr = f"({data_expr} / {data_expr}.dropna().iloc[0]) * 100"
        elif transform == "zscore":
            data_expr = f"({data_expr} - {data_expr}.rolling(252).mean()) / {data_expr}.rolling(252).std()"
        elif transform == "diff":
            data_expr = f"{data_expr}.diff()"
        elif transform == "ma50":
            data_expr = f"{data_expr}.rolling(50).mean()"
        elif transform == "ma200":
            data_expr = f"{data_expr}.rolling(200).mean()"

        # Determine row for subplots
        row = y_axis_idx + 1 if n_panes > 1 else None

        # Build trace
        name_escaped = s_name.replace('"', '\\"')
        visible_str = "True" if visible else '"legendonly"'

        if chart_type == "bar":
            lines.append(f'try:')
            lines.append(f'    _d = {data_expr}.dropna()')
            lines.append(f'    fig.add_trace(go.Bar(x=_d.index, y=_d.values, name="{name_escaped}", visible={visible_str}' +
                         (f', marker_color="{color}"' if color else '') +
                         (f'), row={row}, col=1)' if row else '))'))
            lines.append(f'except Exception: pass')
        elif chart_type in ("area", "stackedarea"):
            lines.append(f'try:')
            lines.append(f'    _d = {data_expr}.dropna()')
            fill = "tozeroy" if chart_type == "area" else "tonexty"
            lines.append(f'    fig.add_trace(go.Scatter(x=_d.index, y=_d.values, name="{name_escaped}", '
                         f'fill="{fill}", visible={visible_str}' +
                         (f', line_color="{color}"' if color else '') +
                         (f'), row={row}, col=1)' if row else '))'))
            lines.append(f'except Exception: pass')
        elif chart_type == "scatter":
            lines.append(f'try:')
            lines.append(f'    _d = {data_expr}.dropna()')
            lines.append(f'    fig.add_trace(go.Scatter(x=_d.index, y=_d.values, name="{name_escaped}", '
                         f'mode="markers", visible={visible_str}' +
                         (f', marker_color="{color}"' if color else '') +
                         (f'), row={row}, col=1)' if row else '))'))
            lines.append(f'except Exception: pass')
        else:  # line (default)
            lines.append(f'try:')
            lines.append(f'    _d = {data_expr}.dropna()')
            lines.append(f'    fig.add_trace(go.Scatter(x=_d.index, y=_d.values, name="{name_escaped}", '
                         f'mode="lines", visible={visible_str}' +
                         (f', line_color="{color}"' if color else '') +
                         (f'), row={row}, col=1)' if row else '))'))
            lines.append(f'except Exception: pass')
        lines.append("")

    # Layout
    title_escaped = title.replace('"', '\\"')
    lines.append("fig.update_layout(")
    if title:
        lines.append(f'    title="{title_escaped}",')
    lines.append(f"    showlegend={show_legend},")
    if legend_pos == "top":
        lines.append(f"    legend=dict(orientation='h', y=1.02, x=0),")
    elif legend_pos == "bottom":
        lines.append(f"    legend=dict(orientation='h', y=-0.1, x=0),")
    lines.append(f"    hovermode='x unified',")
    lines.append(")")
    lines.append("")

    # Gridlines
    if not show_gridlines:
        lines.append("fig.update_xaxes(showgrid=False)")
        lines.append("fig.update_yaxes(showgrid=False)")

    # Apply theme
    lines.append("apply_theme(fig)")

    return "\n".join(lines)


def main():
    with Session(conn.engine) as s:
        # Get existing custom chart names to avoid duplicates
        existing = s.query(Charts.name).filter(Charts.is_deleted == False).all()
        existing_names = {r.name for r in existing}

        # Collect all unique charts from packs that need conversion
        packs = s.query(ChartPack).filter(ChartPack.is_deleted == False).all()

        to_convert = []
        seen_titles = set()

        for p in packs:
            pack_name = p.name
            for c in (p.charts or []):
                if c.get("deleted"):
                    continue
                # Skip if it's already a chart_id reference
                if c.get("chart_id"):
                    continue
                # Skip if no series
                if not c.get("series"):
                    continue
                title = (c.get("title") or "").strip()
                if not title:
                    continue
                # Skip duplicates
                if title in seen_titles:
                    continue
                # Skip if already exists as custom chart
                if title in existing_names:
                    continue
                seen_titles.add(title)
                to_convert.append((pack_name, c))

        print(f"Charts to convert: {len(to_convert)}")

        created = 0
        failed = 0
        skipped = 0

        for pack_name, config in to_convert:
            title = config.get("title", "").strip()
            code = generate_custom_code(config)

            if not code:
                skipped += 1
                continue

            try:
                # Create the Custom Chart
                chart = Charts(
                    created_by_user_id=YOUR_ID,
                    code=code,
                    name=title,
                    category=pack_name,
                    description=f"Converted from chartpack: {pack_name}",
                    tags=[pack_name.lower().replace(" ", "-")],
                    public=True,
                    rank=created,
                )
                s.add(chart)
                s.flush()
                created += 1

                if created % 20 == 0:
                    print(f"  ... {created} created")

            except Exception as e:
                failed += 1
                print(f"  FAILED: {title} — {e}")
                s.rollback()

        s.commit()
        print(f"\nDone!")
        print(f"  Created: {created}")
        print(f"  Failed: {failed}")
        print(f"  Skipped (no code/series): {skipped}")
        print(f"  Total Custom Charts now: {created + len(existing_names)}")


if __name__ == "__main__":
    main()
