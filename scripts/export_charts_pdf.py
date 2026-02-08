"""
PDF Export Script for Investment-X Charts.

Generates a professional multi-page PDF report from charts stored in the database.
Preserves the academic styling from ix.cht.style.
"""

import os
import sys
import tempfile
from datetime import datetime

import plotly.graph_objects as go
import plotly.io as pio
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

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
    "Performance",
    "RRG",
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


def export_charts_to_pdf(output_path: str = "investment_x_charts.pdf"):
    """
    Assembles a professional multi-page PDF report.
    Preserves the academic styling from the chart definitions.

    Args:
        output_path: Path to save the PDF file
    """
    print(f"Connecting to database...")

    with Session() as session:
        # Load all charts and sort using custom ordering
        charts_raw = session.query(Chart).all()
        charts = sort_charts(charts_raw)

        if not charts:
            print("No charts found in database.")
            return

        print(f"Found {len(charts)} charts. Generating PDF report...")

        landscape_a4 = landscape(A4)
        c = canvas.Canvas(output_path, pagesize=landscape_a4)
        width, height = landscape_a4

        # 1. Cover Page
        draw_cover_page(c, width, height)

        # 2. Charts
        page_num = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, chart in enumerate(charts):
                try:
                    chart_name = get_chart_name(chart)
                    category = get_effective_category(chart)
                    print(
                        f"[{i+1}/{len(charts)}] Processing: {chart_name} ({category})"
                    )

                    # Skip charts without cached figures
                    if not chart.figure:
                        print(f"  Skipping: No cached figure available")
                        continue

                    fig_dict = chart.figure
                    fig = go.Figure(fig_dict)

                    # Scale up fonts for PDF readability (1.8x multiplier)
                    scale_factor = 1.8

                    # Scale global font
                    current_font_size = (
                        fig.layout.font.size
                        if fig.layout.font and fig.layout.font.size
                        else 12
                    )
                    fig.update_layout(font=dict(size=current_font_size * scale_factor))

                    # Scale title font
                    if fig.layout.title and fig.layout.title.font:
                        title_size = (
                            fig.layout.title.font.size
                            if fig.layout.title.font.size
                            else 14
                        )
                        fig.update_layout(
                            title=dict(font=dict(size=title_size * scale_factor))
                        )

                    # Scale axis fonts
                    fig.for_each_xaxis(
                        lambda x: x.update(
                            title_font_size=(
                                x.title.font.size
                                if x.title and x.title.font and x.title.font.size
                                else 12
                            )
                            * scale_factor,
                            tickfont_size=(
                                x.tickfont.size
                                if x.tickfont and x.tickfont.size
                                else 10
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
                                y.tickfont.size
                                if y.tickfont and y.tickfont.size
                                else 10
                            )
                            * scale_factor,
                        )
                    )

                    # Scale legend font
                    legend_size = 10
                    if (
                        fig.layout.legend
                        and fig.layout.legend.font
                        and fig.layout.legend.font.size
                    ):
                        legend_size = fig.layout.legend.font.size
                    fig.update_layout(
                        legend=dict(font=dict(size=legend_size * scale_factor))
                    )

                    # Adjust layout for PDF - larger margins to prevent overlap
                    fig.update_layout(
                        width=1600,
                        height=900,
                        margin=dict(l=100, r=60, t=180, b=80),
                    )

                    # High-res export
                    img_path = os.path.join(temp_dir, f"chart_{i}.png")
                    pio.write_image(
                        fig, img_path, format="png", width=1600, height=900, scale=2
                    )

                    # Header bar
                    c.setFillColor(DARK_BLUE)
                    c.rect(0, height - 40, width, 40, fill=1, stroke=0)
                    c.setFillColor(HexColor("#ffffff"))
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(30, height - 25, f"Macro Report | {category}")

                    # Chart Image Positioning - position below header
                    img_w = width * 0.92
                    img_ratio = 900 / 1600  # height/width ratio
                    img_h = img_w * img_ratio

                    x_pos = (width - img_w) / 2
                    y_pos = 80  # Space from bottom for description

                    c.drawImage(img_path, x_pos, y_pos, width=img_w, height=img_h)

                    # Bottom Description Area
                    if chart.description:
                        c.setFillColor(TEXT_COLOR)
                        c.setFont("Helvetica-Bold", 11)
                        c.drawString(x_pos, 85, "ANALYSIS & CONTEXT:")

                        c.setFont("Helvetica", 10)
                        c.setFillColor(GREY_COLOR)

                        # Basic multi-line text wrapping
                        text = chart.description
                        description_words = text.split()
                        lines = []
                        current_line = ""
                        for word in description_words:
                            if len(current_line + " " + word) < 120:
                                current_line += " " + word
                            else:
                                lines.append(current_line.strip())
                                current_line = word
                        lines.append(current_line.strip())

                        text_y = 70
                        for line_text in lines[:3]:  # Max 3 lines to fit
                            c.drawString(x_pos, text_y, line_text)
                            text_y -= 13

                    # Footer
                    c.setFillColor(GREY_COLOR)
                    c.setFont("Helvetica", 9)
                    c.drawString(30, 20, "Confidential | Investment-X")
                    c.drawRightString(width - 30, 20, f"Page {page_num}")

                    c.showPage()
                    page_num += 1

                except Exception as e:
                    print(f"  Error: {e}")
                    import traceback

                    traceback.print_exc()

            c.save()
            print(f"\nPDF Report Success: {output_path}")
            print(f"Total pages: {page_num} (including cover)")


if __name__ == "__main__":
    export_charts_to_pdf()
