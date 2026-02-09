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
def export_charts_pdf():
    """
    Generates and downloads a PDF report of all charts.
    """
    from datetime import datetime
    from fastapi.responses import StreamingResponse
    from ix.misc.scripts import export_charts_to_pdf
    import io

    # Generate PDF bytes using the centralized script logic
    pdf_content = export_charts_to_pdf(output_path=None)

    if not pdf_content:
        return {"error": "No charts found to export"}

    filename = f"Investment-X_Macro_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
