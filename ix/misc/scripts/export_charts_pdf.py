"""
PDF Export Script for Investment-X Charts.

Generates a professional multi-page PDF report from charts stored in the database.
Preserves the academic styling from ix.cht.style.
"""

import os
import sys
import tempfile
import shutil
import concurrent.futures
import threading
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# Global Lock for Kaleido image export
KALEIDO_LOCK = threading.Lock()

# Disable MathJax to prevent serialization errors in Kaleido
try:
    pio.kaleido.scope.mathjax = None
except Exception:
    pass

# Ensure ix is in path
sys.path.append(os.getcwd())

from ix.db.conn import Session
from ix.db.models import Chart

# Color Scheme
DARK_BLUE = HexColor("#2c2f7a")
TEXT_COLOR = HexColor("#1e293b")
GREY_COLOR = HexColor("#64748b")
MAGENTA = HexColor("#ff00b8")

# Preferred category order for the PDF report
CATEGORY_ORDER = [
    "Performance",
    "RRG",
    "Positions",
    "Business",
    "Composite",
    "Earnings",
    "Liquidity",
    "Credit",
    "Fiscal",
    "Debt",
    "Financial",
    "Consumer",
    "Inflation",
    "Surprise",
    "Gold",
    "OECD",
    "LongTerm",
    "Uncategorized",
]

# Chart name to category mapping (for charts without category in DB)
CHART_CATEGORY_MAP = {
    # Performance
    "Performance_GlobalEquity_1W": "Performance",
    "Performance_GlobalEquity_1M": "Performance",
    "Performance_USSectors_1W": "Performance",
    "Performance_USSectors_1M": "Performance",
    # RRG
    "RelativeRotation_UsSectors_Dynamic": "RRG",
    "RelativeRotation_UsSectors_Tactical": "RRG",
    "RelativeRotation_UsSectors_Strategic": "RRG",
    "RelativeRotation_GlobalEquities_Dynamic": "RRG",
    "RelativeRotation_GlobalEquities_Tactical": "RRG",
    "RelativeRotation_GlobalEquities_Strategic": "RRG",
    "RelativeRotation_KrSectors_Dynamic": "RRG",
    "RelativeRotation_KrSectors_Tactical": "RRG",
    "RelativeRotation_KrSectors_Strategic": "RRG",
    # Business
    "AsianExportsYoY": "Business",
    "Mag7CapexGrowth": "Business",
    "IndustrialProductionLeadingIndicator": "Business",
    "HeavyTruckSalesUnemployment": "Business",
    "EmpireStateManufacturing": "Business",
    # Composite
    "CompositeLeadingIndicator": "Composite",
    "CompositeLeadingIndicators": "Composite",
    "IsmSwedenPmi": "Composite",
    "MarketCompositeViews": "Composite",
    # Earnings
    "EarningsRevisionBreadth": "Earnings",
    "EarningsGrowth_NTMA": "Earnings",
    "SPX_EqualWeight_SectorEarningsContribution": "Earnings",
    "SPX_EqualWeight_SectorEarningsImpulse": "Earnings",
    # Liquidity
    "GlobalLiquidity": "Liquidity",
    "GlobalLiquidityYoY": "Liquidity",
    "GlobalAssetContribution": "Liquidity",
    "GlobalMoneySupplyContribution": "Liquidity",
    "FedLiquidityImpulse": "Liquidity",
    # Credit
    "US_CreditImpulse": "Credit",
    "US_CreditImpulseToGDP": "Credit",
    "BankCreditOutlook": "Credit",
    # Fiscal
    "USFederalDeficitYieldCurve": "Fiscal",
    "UsGovNetOutlays_InterestPayments": "Fiscal",
    "UsGovNetOutlays_NationalDefense": "Fiscal",
    "UsGovNetOutlays_SocialCredit": "Fiscal",
    # Debt
    "USFederalDebt": "Debt",
    # Financial
    "FinancialConditions": "Financial",
    "FinancialConditionsComponents": "Financial",
    # Consumer
    "MedianWageByQuartile": "Consumer",
    # Inflation
    "CpiIsmPriceIndicators": "Inflation",
    # Surprise
    "USSurpriseUST10YCycle": "Surprise",
    "USSurpriseDollarCycle": "Surprise",
    # Gold
    "GoldBullMarkets": "Gold",
    # OECD
    "OecdCliDiffusion": "OECD",
    # LongTerm
    "LongTermCycles_Kospi": "LongTerm",
    "LongTermCycles_SPX": "LongTerm",
    "LongTermCycles_GOLD": "LongTerm",
    "LongTermCycles_SILVER": "LongTerm",
    "LongTermCycles_CRUDE": "LongTerm",
    "LongTermCycles_DXY": "LongTerm",
    "LongTermCycles_NKY": "LongTerm",
    "LongTermCycles_CCMP": "LongTerm",
    "LongTermCycles_DAX": "LongTerm",
    "LongTermCycles_SHCOMP": "LongTerm",
}


def draw_cover_page(c, width, height):
    """Draw a professional cover page."""
    # Background Accent
    c.setFillColor(DARK_BLUE)
    c.rect(0, height - 150, width, 150, fill=1, stroke=0)

    # Title
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 48)
    c.drawString(60, height - 100, "INVESTMENT-X")

    c.setFillColor(TEXT_COLOR)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(60, height - 250, "Global Macro Chartbook")

    # Date
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(TEXT_COLOR)
    c.drawString(60, 60, f"Generated on {datetime.now().strftime('%B %d, %Y')}")

    # Accent Line
    c.setStrokeColor(MAGENTA)
    c.setLineWidth(5)
    c.line(60, height - 265, 300, height - 265)

    c.showPage()


def get_chart_name(chart: Chart) -> str:
    """
    Extracts a display name from the chart code.

    Args:
        chart: Chart model instance

    Returns:
        Human-readable chart name derived from code
    """
    code = chart.code.strip()

    # Remove "cht." prefix if present
    if code.startswith("cht."):
        code = code[4:]

    # Remove "()" suffix if present
    if code.endswith("()"):
        code = code[:-2]

    return code


def get_effective_category(chart: Chart) -> str:
    """
    Get the effective category for a chart.
    Uses DB category if available, otherwise falls back to CHART_CATEGORY_MAP.

    Args:
        chart: Chart model instance

    Returns:
        Category string
    """
    # If chart has category in DB, use it
    if chart.category:
        return chart.category

    # Fallback to mapping
    chart_name = get_chart_name(chart)
    return CHART_CATEGORY_MAP.get(chart_name, "Uncategorized")


def sort_charts(charts: list) -> list:
    """
    Sort charts by category order, then by name within each category.

    Args:
        charts: List of Chart model instances

    Returns:
        Sorted list of charts
    """

    def sort_key(chart):
        category = get_effective_category(chart)
        # Get category order index (unknown categories go to end)
        try:
            cat_order = CATEGORY_ORDER.index(category)
        except ValueError:
            cat_order = len(CATEGORY_ORDER)

        chart_name = get_chart_name(chart)
        return (cat_order, chart_name)

    return sorted(charts, key=sort_key)


def process_chart_image(chart, temp_dir, i):
    """Worker function to generate image for a single chart."""
    try:
        if not chart.figure:
            return None

        # Build cache path
        cache_dir = Path("ix/data/chart_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Use filename that includes timestamp to handle updates
        ts_str = chart.updated_at.strftime("%Y%m%d_%H%M%S") if chart.updated_at else "0"
        cache_path = cache_dir / f"{chart.code}_{ts_str}.png"

        # Check cache
        if cache_path.exists():
            # Copy to temp_dir for aggregation
            dest_path = Path(temp_dir) / f"chart_{i}.png"
            shutil.copy(cache_path, dest_path)
            return {
                "path": str(dest_path),
                "category": get_effective_category(chart),
                "description": chart.description,
                "index": i,
            }

        # Otherwise generate
        fig_dict = chart.figure
        fig = go.Figure(fig_dict)

        # Scale up fonts for PDF readability (1.8x multiplier)
        scale_factor = 1.8
        current_font_size = (
            fig.layout.font.size if fig.layout.font and fig.layout.font.size else 12
        )
        fig.update_layout(font=dict(size=current_font_size * scale_factor))

        if fig.layout.title and fig.layout.title.font:
            title_size = (
                fig.layout.title.font.size if fig.layout.title.font.size else 14
            )
            fig.update_layout(title=dict(font=dict(size=title_size * scale_factor)))

        fig.for_each_xaxis(
            lambda x: x.update(
                title_font_size=(
                    x.title.font.size
                    if x.title and x.title.font and x.title.font.size
                    else 12
                )
                * scale_factor,
                tickfont_size=(
                    x.tickfont.size if x.tickfont and x.tickfont.size else 10
                )
                * scale_factor,
            )
        )
        fig.for_each_yaxis(
            lambda y: y.update(
                title_font_size=(
                    y.title.font.size
                    if y.title and y.title.font and y.title.font.size
                    else 12
                )
                * scale_factor,
                tickfont_size=(
                    y.tickfont.size if y.tickfont and y.tickfont.size else 10
                )
                * scale_factor,
            )
        )

        legend_size = 10
        if fig.layout.legend and fig.layout.legend.font and fig.layout.legend.font.size:
            legend_size = fig.layout.legend.font.size
        fig.update_layout(legend=dict(font=dict(size=legend_size * scale_factor)))

        fig.update_layout(
            width=1600,
            height=900,
            margin=dict(l=100, r=60, t=180, b=80),
            autosize=False,
        )

        # Save to cache AND temp
        dest_path = Path(temp_dir) / f"chart_{i}.png"

        # Use a lock to prevent concurrent serialization issues in Kaleido
        with KALEIDO_LOCK:
            try:
                # Use to_image specifically as it sometimes handles serialization better than write_image
                img_bytes = pio.to_image(
                    fig, format="png", width=1600, height=900, scale=2, engine="kaleido"
                )
                with open(dest_path, "wb") as f:
                    f.write(img_bytes)
            except Exception as e:
                # Fallback: try to export without custom layout scaling if it fails
                if "serialize" in str(e).lower() or "uncaught" in str(e).lower():
                    print(
                        f"  Warning: Serialization failed for {chart.code}, retrying with basic layout..."
                    )
                    fig.update_layout(font=dict(size=12))  # Reset font
                    img_bytes = pio.to_image(
                        fig,
                        format="png",
                        width=1200,
                        height=700,
                        scale=1.5,
                        engine="kaleido",
                    )
                    with open(dest_path, "wb") as f:
                        f.write(img_bytes)
                else:
                    raise e
        # Prune old cache files for this chart
        for old_file in cache_dir.glob(f"{chart.code}_*.png"):
            try:
                old_file.unlink()
            except:
                pass
        shutil.copy(dest_path, cache_path)

        return {
            "path": str(dest_path),
            "category": get_effective_category(chart),
            "description": chart.description,
            "index": i,
        }
    except Exception as e:
        print(f"  Error processing {chart.code}: {e}")
        return None


def export_charts_to_pdf(output_path: str = "investment_x_charts.pdf") -> bytes | None:
    """
    Assembles a professional multi-page PDF report.
    Uses parallel processing and caching for high performance.
    """
    print(f"Connecting to database...")
    import io

    with Session() as session:
        charts_raw = session.query(Chart).all()
        charts = sort_charts(charts_raw)

        if not charts:
            print("No charts found in database.")
            return None

        print(f"Found {len(charts)} charts. Starting parallel image generation...")

        landscape_a4 = landscape(A4)
        buffer = io.BytesIO() if output_path is None else None
        c = (
            canvas.Canvas(buffer, pagesize=landscape_a4)
            if output_path is None
            else canvas.Canvas(output_path, pagesize=landscape_a4)
        )
        width, height = landscape_a4

        # 1. Cover
        draw_cover_page(c, width, height)

        # 2. Generate images in parallel
        processed_results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            # Reduced concurrency to minimize resource contention
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(process_chart_image, chart, temp_dir, i)
                    for i, chart in enumerate(charts)
                ]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        processed_results.append(res)

            # Sort results back to original order
            processed_results.sort(key=lambda x: x["index"])

            # 3. Assemble PDF
            for i, res in enumerate(processed_results):
                page_num = i + 1
                img_path = res["path"]
                category = res["category"]
                description = res["description"]

                # Header bar
                c.setFillColor(DARK_BLUE)
                c.rect(0, height - 40, width, 40, fill=1, stroke=0)
                c.setFillColor(HexColor("#ffffff"))
                c.setFont("Helvetica-Bold", 14)
                c.drawString(30, height - 25, f"Macro Report | {category}")

                # Chart Image
                img_w = width * 0.92
                img_h = img_w * (900 / 1600)
                x_pos = (width - img_w) / 2
                y_pos = 80
                c.drawImage(img_path, x_pos, y_pos, width=img_w, height=img_h)

                # Description
                if description:
                    c.setFillColor(TEXT_COLOR)
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(x_pos, 85, "ANALYSIS & CONTEXT:")
                    c.setFont("Helvetica", 10)
                    c.setFillColor(GREY_COLOR)
                    words = description.split()
                    lines, current_line = [], ""
                    for word in words:
                        if len(current_line + " " + word) < 120:
                            current_line += " " + word
                        else:
                            lines.append(current_line.strip())
                            current_line = word
                    lines.append(current_line.strip())
                    text_y = 70
                    for line_text in lines[:3]:
                        c.drawString(x_pos, text_y, line_text)
                        text_y -= 13

                # Footer
                c.setFillColor(GREY_COLOR)
                c.setFont("Helvetica", 9)
                c.drawString(30, 20, "Confidential | Investment-X")
                c.drawRightString(width - 30, 20, f"Page {page_num}")
                c.showPage()

            c.save()
            print(f"\nPDF Report Success: {output_path or 'Memory Buffer'}")

            if buffer:
                pdf_bytes = buffer.getvalue()
                buffer.close()
                return pdf_bytes
            return None


if __name__ == "__main__":
    export_charts_to_pdf()
