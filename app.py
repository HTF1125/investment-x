from __future__ import annotations

import io
from typing import List

import dash
from dash import Dash, html, dcc, Output, Input, callback
import plotly.graph_objects as go
import plotly.io as pio

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader


# ---------- Create sample figures ----------
def make_figures() -> List[go.Figure]:
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(y=[1, 3, 2, 4, 3, 5], mode="lines+markers", name="Series A")
    )
    fig1.update_layout(
        title="Line Chart Example", xaxis_title="Index", yaxis_title="Value"
    )

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=["A", "B", "C", "D"], y=[5, 2, 6, 3], name="Bars"))
    fig2.update_layout(
        title="Bar Chart Example", xaxis_title="Category", yaxis_title="Value"
    )

    return [fig1, fig2]


# ---------- PDF Builder ----------
def build_pdf_bytes(
    figures: List[go.Figure], scale: int = 2, width: int = 900, height: int = 600
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    for idx, fig in enumerate(figures, start=1):
        try:
            # Explicitly request Kaleido engine
            png_bytes = pio.to_image(
                fig,
                format="png",
                engine="kaleido",
                scale=scale,
                width=width,
                height=height,
            )
            img = ImageReader(io.BytesIO(png_bytes))
            page_width, page_height = letter
            c.drawImage(
                img,
                0,
                0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=True,
                anchor="c",
            )
        except Exception as e:
            # Fallback: write error text if export fails
            c.setFont("Helvetica", 14)
            c.drawString(50, 700, f"Figure {idx} could not be exported: {e}")
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.read()


# ---------- Dash App ----------
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={
        "maxWidth": "900px",
        "margin": "40px auto",
        "fontFamily": "system-ui, sans-serif",
    },
    children=[
        html.H2("Plotly → Multi-page PDF Download"),
        html.P("Click the button to export the charts below into a single PDF."),
        dcc.Graph(figure=make_figures()[0], id="fig-1"),
        dcc.Graph(figure=make_figures()[1], id="fig-2"),
        html.Button(
            "⬇️ Download PDF", id="btn-download", n_clicks=0, style={"marginTop": "20px"}
        ),
        dcc.Download(id="download-pdf"),
    ],
)


@callback(
    Output("download-pdf", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True,
)
def trigger_download(n_clicks: int):
    figs = make_figures()
    pdf_bytes = build_pdf_bytes(figs)
    return dcc.send_bytes(lambda f: f.write(pdf_bytes), filename="charts.pdf")


if __name__ == "__main__":
    app.run_server(debug=True)
