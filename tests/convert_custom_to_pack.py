"""Convert remaining Custom Charts into ChartPack chart configs.

For each Custom Chart not already in a pack:
1. Parse its cached figure traces to generate series config
2. Extract data-fetching code
3. Add as a chart config to the appropriate ChartPack (by category)
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ix.db.conn import conn
conn.connect()

from sqlalchemy.orm import Session
from ix.db.models import Charts
from ix.db.models.chart_pack import ChartPack

YOUR_ID = "096862b7-b643-40a5-9f58-e41a39520fc0"


def figure_to_series_config(figure: dict) -> list:
    """Extract series config from a Plotly figure's traces."""
    if not figure or not figure.get("data"):
        return []

    series = []
    for i, trace in enumerate(figure["data"]):
        trace_type = trace.get("type", "scatter")
        name = trace.get("name", f"Series {i+1}")
        visible = trace.get("visible", True)
        yaxis = trace.get("yaxis", "y")

        # Map Plotly trace type to chartpack chart type
        if trace_type == "bar":
            chart_type = "bar"
        elif trace.get("fill") in ("tozeroy", "tonexty"):
            chart_type = "area"
        elif trace.get("mode") == "markers":
            chart_type = "scatter"
        else:
            chart_type = "line"

        # Extract color
        color = ""
        if trace.get("line", {}).get("color"):
            color = trace["line"]["color"]
        elif trace.get("marker", {}).get("color"):
            mc = trace["marker"]["color"]
            if isinstance(mc, str):
                color = mc

        # Determine y-axis index (y, y2, y3 -> 0, 1, 2)
        y_axis_index = 0
        if yaxis and yaxis != "y":
            try:
                y_axis_index = int(yaxis.replace("y", "")) - 1
            except (ValueError, TypeError):
                pass

        series.append({
            "code": name,  # Column name = trace name
            "name": name,
            "chartType": chart_type,
            "color": color,
            "yAxis": "left" if y_axis_index == 0 else "right",
            "yAxisIndex": y_axis_index,
            "visible": visible if visible is True else False,
            "transform": "none",
        })

    return series


def extract_data_code(full_code: str) -> str:
    """Try to extract just the data-fetching portion of the code.

    Returns the full code as-is — the chartpack code field
    stores whatever code is needed to produce data.
    """
    # The code will be stored in the chartpack config's `code` field.
    # For display purposes, we keep it as-is.
    return full_code


def main():
    with Session(conn.engine) as s:
        # Find Custom Charts not already in any pack
        packs = s.query(ChartPack).filter(ChartPack.is_deleted == False).all()
        existing_ids = set()
        for p in packs:
            for c in (p.charts or []):
                cid = c.get("chart_id")
                if cid:
                    existing_ids.add(cid)

        charts = s.query(Charts).filter(Charts.is_deleted == False).all()
        to_convert = [c for c in charts if str(c.id) not in existing_ids]

        print(f"Charts to convert: {len(to_convert)}")

        # Group by category
        by_category = {}
        for c in to_convert:
            cat = c.category or "Uncategorized"
            by_category.setdefault(cat, []).append(c)

        # For each category, find or create a pack and add the charts
        for category, chart_list in by_category.items():
            # Find existing pack with this name
            pack = s.query(ChartPack).filter(
                ChartPack.name == category,
                ChartPack.is_deleted == False,
            ).first()

            if not pack:
                # Create new pack
                pack = ChartPack(
                    user_id=YOUR_ID,
                    name=category,
                    description=f"Charts from {category} category",
                    charts=[],
                    is_published=True,
                )
                s.add(pack)
                s.flush()
                print(f"  Created new pack: {category}")

            current_charts = list(pack.charts or [])

            for chart in chart_list:
                # Generate series config from figure
                series = figure_to_series_config(chart.figure) if chart.figure else []

                # Build chartpack chart config
                config = {
                    "title": chart.name or "Untitled",
                    "code": chart.code or "",
                    "series": series,
                    "figure": chart.figure,  # Pre-cached for immediate display
                    "panes": [{"id": 0, "label": ""}],
                    "showLegend": True,
                    "showGridlines": True,
                    "legendPosition": "top",
                    "hoverMode": "x unified",
                    "activeRange": "MAX",
                    "chart_id": str(chart.id),  # Reference back to Custom Chart
                }

                # Check for multi-pane (if figure has multiple y-axes)
                if chart.figure:
                    layout = chart.figure.get("layout", {})
                    max_yaxis = 0
                    for key in layout:
                        if key.startswith("yaxis") and key != "yaxis":
                            try:
                                idx = int(key.replace("yaxis", ""))
                                max_yaxis = max(max_yaxis, idx)
                            except ValueError:
                                pass
                    if max_yaxis > 1:
                        config["panes"] = [{"id": i, "label": ""} for i in range(max_yaxis)]

                current_charts.append(config)
                print(f"  Added: {chart.name} -> {category}")

            pack.charts = current_charts
            s.flush()

        s.commit()
        print(f"\nDone! Converted {len(to_convert)} charts into ChartPack format.")

        # Summary
        for cat, cl in by_category.items():
            print(f"  {cat}: {len(cl)} charts added")


if __name__ == "__main__":
    main()
