from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import plotly.io as pio
import plotly.graph_objects as go
from sqlalchemy.orm import Session
from ix.db.conn import ensure_connection, Session
from ix.db.models import Chart

# We no longer import chart classes to plot here, since we read from DB
# but we might still want to trigger an update if necessary.
# For now, just READ.

router = APIRouter()


@router.get("/charts", response_class=HTMLResponse)
async def get_all_charts():
    """
    Shows all charts stored in the database.
    """
    charts_html = ""

    with Session() as session:
        # Retrieve all charts ordered by name or category
        charts = session.query(Chart).order_by(Chart.category, Chart.name).all()

        if not charts:
            charts_html = """
            <div style="text-align: center; margin-top: 50px;">
                <h2>No charts found in the database.</h2>
                <p>Please run the chart generation tasks to populate the database.</p>
            </div>
            """
        else:
            for chart in charts:
                try:
                    # chart.figure is a dict (JSONB), convert to Figure object
                    fig = go.Figure(chart.figure)

                    # Convert to HTML div
                    chart_div = pio.to_html(
                        fig, full_html=False, include_plotlyjs="cdn"
                    )

                    meta_info = (
                        f"<p style='text-align: center; color: #888; font-size: 0.9em;'>Category: {chart.category} | Updated: {chart.updated_at.strftime('%Y-%m-%d %H:%M')}</p>"
                        if chart.updated_at
                        else ""
                    )
                    desc = (
                        f"<p style='text-align: center;'>{chart.description}</p>"
                        if chart.description
                        else ""
                    )

                    charts_html += f"""
                    <div style="margin-bottom: 60px; background-color: #222; padding: 20px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; text-align: center;">
                        <h2>{chart.name}</h2>
                        {desc}
                        {meta_info}
                        {chart_div}
                    </div>
                    """
                except Exception as e:
                    charts_html += f"""
                    <div style="margin-bottom: 50px; color: red;">
                        <h2>Error rendering {chart.name}</h2>
                        <p>{str(e)}</p>
                    </div>
                    <hr>
                    """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Investment-X Charts</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 40px; background-color: #121212; color: #e0e0e0; }}
            h1 {{ color: #ffffff; text-align: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }}
            h2 {{ color: #ffffff; text-align: center; margin-top: 0; }}
            hr {{ border: 0; border-top: 1px solid #333; margin: 40px 0; }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h1 >Investment-X Chart Dashboard</h1>
        <div style="max-width: 1200px; margin: 0 auto;">
            {charts_html}
        </div>
    </body>
    </html>
    """
    return full_html


@router.get("/charts/export/pdf")
async def export_charts_pdf():
    """
    Generates and downloads a PDF report of all charts.
    """
    import os
    import io
    import tempfile
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    import plotly.io as pio
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    # Color Scheme
    DARK_BLUE = HexColor("#2c2f7a")
    TEXT_COLOR = HexColor("#1e293b")
    GREY_COLOR = HexColor("#64748b")
    MAGENTA = HexColor("#ff00b8")

    # Category order
    CATEGORY_ORDER = [
        "Performance",
        "RRG",
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

    def get_effective_category(chart):
        return chart.category or "Uncategorized"

    def sort_charts(charts):
        def sort_key(chart):
            category = get_effective_category(chart)
            try:
                cat_order = CATEGORY_ORDER.index(category)
            except ValueError:
                cat_order = len(CATEGORY_ORDER)
            return (cat_order, chart.code)

        return sorted(charts, key=sort_key)

    # Generate PDF in temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, "investment_x_charts.pdf")

        with Session() as session:
            charts_raw = session.query(Chart).all()
            charts = sort_charts(charts_raw)

            landscape_a4 = landscape(A4)
            c = canvas.Canvas(pdf_path, pagesize=landscape_a4)
            width, height = landscape_a4

            # Cover Page
            c.setFillColor(DARK_BLUE)
            c.rect(0, height - 150, width, 150, fill=1, stroke=0)
            c.setFillColor(HexColor("#ffffff"))
            c.setFont("Helvetica-Bold", 48)
            c.drawString(60, height - 100, "INVESTMENT-X")
            c.setFillColor(TEXT_COLOR)
            c.setFont("Helvetica-Bold", 32)
            c.drawString(60, height - 250, "Global Macro Chartbook")
            c.setFont("Helvetica-Bold", 14)
            c.drawString(60, 60, f"Generated on {datetime.now().strftime('%B %d, %Y')}")
            c.setStrokeColor(MAGENTA)
            c.setLineWidth(5)
            c.line(60, height - 265, 300, height - 265)
            c.showPage()

            # Charts
            page_num = 1
            for chart in charts:
                if not chart.figure:
                    continue

                try:
                    fig = go.Figure(chart.figure)
                    fig.update_layout(
                        width=1600,
                        height=900,
                        margin=dict(l=100, r=60, t=180, b=80),
                        font=dict(size=21),
                    )

                    img_path = os.path.join(temp_dir, f"chart_{page_num}.png")
                    pio.write_image(
                        fig, img_path, format="png", width=1600, height=900, scale=2
                    )

                    category = get_effective_category(chart)

                    # Header
                    c.setFillColor(DARK_BLUE)
                    c.rect(0, height - 40, width, 40, fill=1, stroke=0)
                    c.setFillColor(HexColor("#ffffff"))
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(30, height - 25, f"Macro Report | {category}")

                    # Chart Image
                    img_w = width * 0.92
                    img_h = img_w * (900 / 1600)
                    x_pos = (width - img_w) / 2
                    y_pos = 50
                    c.drawImage(img_path, x_pos, y_pos, width=img_w, height=img_h)

                    # Footer
                    c.setFillColor(GREY_COLOR)
                    c.setFont("Helvetica", 9)
                    c.drawString(30, 20, "Confidential | Investment-X")
                    c.drawRightString(width - 30, 20, f"Page {page_num}")

                    c.showPage()
                    page_num += 1
                except Exception:
                    continue

            c.save()

        # Read PDF into memory before temp dir is deleted
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

    # Return as streaming response
    filename = f"investment_x_charts_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
