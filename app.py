import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from ix import Series
import pandas as pd
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile
import os

# Set page config
st.set_page_config(
    page_title="Tech Companies CAPEX Analysis", page_icon="📊", layout="wide"
)

# Title and description
st.title("📊 Tech Companies CAPEX Analysis")
st.markdown("Analyzing quarterly capital expenditure data for major tech companies")


# Data processing function
@st.cache_data
def load_data():
    # Forward-looking CAPEX data
    ff_data = {
        code: Series(f"{code}:FF_CAPEX_Q")
        for code in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]
    }

    ff = (
        pd.DataFrame(ff_data)
        .resample("B")
        .last()
        .ffill()
        .dropna()
        .reindex(pd.date_range("2010-1-1", pd.Timestamp("today")))
        .ffill()
    )

    # Historical CAPEX data
    fe_data = {
        code: Series(f"{code}:FE_CAPEX_Q")
        for code in ["NVDA", "MSFT", "AMZN", "META", "GOOG"]
    }

    fe = pd.DataFrame(fe_data).resample("B").last().ffill().dropna()

    return ff, fe


# PDF generation function
def generate_pdf_report(fig, weekly_pct_change, ff, fe):
    """Generate a PDF report with the plot and data"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center alignment
    )

    # Build content
    story = []

    # Title
    story.append(Paragraph("Tech Companies CAPEX Analysis Report", title_style))
    story.append(Spacer(1, 12))

    # Description
    story.append(
        Paragraph(
            "Analyzing quarterly capital expenditure data for major tech companies (NVDA, MSFT, AMZN, META, GOOG)",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 20))

    # Save plot as image
    tmp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file_path = tmp_file.name

        # Try using kaleido first (faster and better quality)
        try:
            fig.write_image(tmp_file_path, width=800, height=600, scale=2)
        except Exception as kaleido_error:
            # Fallback to matplotlib if kaleido fails
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # Create matplotlib figure
            plt.figure(figsize=(12, 8))
            plt.plot(
                weekly_pct_change.index,
                weekly_pct_change.values * 100,
                color="#1f77b4",
                linewidth=2,
                label="Weekly CAPEX % Change (52-week)",
            )
            plt.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
            plt.title(
                "Tech Companies CAPEX - 52-Week Percentage Change", fontsize=16, pad=20
            )
            plt.xlabel("Date", fontsize=12)
            plt.ylabel("Percentage Change (%)", fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()

            # Save with matplotlib
            plt.savefig(
                tmp_file_path,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            plt.close()

        # Add plot to PDF
        story.append(
            Paragraph("CAPEX 52-Week Percentage Change Chart", styles["Heading2"])
        )
        story.append(Spacer(1, 12))

        # Add image - keep file reference until PDF is built
        img = Image(tmp_file_path, width=7 * inch, height=5.25 * inch)
        story.append(img)
        story.append(Spacer(1, 20))

    except Exception as e:
        # If there's an error, clean up the temp file
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        raise e

    # Add statistics
    story.append(Paragraph("Key Statistics", styles["Heading2"]))
    story.append(Spacer(1, 12))

    if len(weekly_pct_change) > 0:
        current_change = weekly_pct_change.iloc[-1] * 100
        max_change = weekly_pct_change.max() * 100
        min_change = weekly_pct_change.min() * 100

        stats_data = [
            ["Metric", "Value"],
            ["Current % Change", f"{current_change:.2f}%"],
            ["Maximum % Change", f"{max_change:.2f}%"],
            ["Minimum % Change", f"{min_change:.2f}%"],
        ]

        stats_table = Table(stats_data)
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(stats_table)
        story.append(Spacer(1, 20))

    # Add recent data table
    story.append(Paragraph("Recent Data (Last 10 Observations)", styles["Heading2"]))
    story.append(Spacer(1, 12))

    recent_data = weekly_pct_change.tail(10).to_frame("52-Week % Change")
    recent_data["Date"] = recent_data.index.strftime("%Y-%m-%d")
    recent_data["% Change"] = (recent_data["52-Week % Change"] * 100).round(2).astype(
        str
    ) + "%"
    recent_data = recent_data[["Date", "% Change"]].reset_index(drop=True)

    # Convert to list for table
    table_data = [["Date", "% Change"]] + recent_data.values.tolist()

    data_table = Table(table_data)
    data_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ]
        )
    )

    story.append(data_table)
    story.append(Spacer(1, 20))

    # Add global markets table to PDF
    try:
        # Load global markets data for PDF
        global_data = {
            "ACWI": Series("ACWI US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "US": Series("SPY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "DM ex US": Series("IDEV US Equity:PX_LAST", freq="ME")
            .pct_change()
            .iloc[-13:]
            * 100,
            "U.K.": Series("EWU US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "EAFE": Series("EFA US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Europe": Series("FEZ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Germany": Series("EWG US Equity:PX_LAST", freq="ME")
            .pct_change()
            .iloc[-13:]
            * 100,
            "Japan": Series("EWJ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Korea": Series("EWY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Australia": Series("EWA US Equity:PX_LAST", freq="ME")
            .pct_change()
            .iloc[-13:]
            * 100,
            "Emerging": Series("VWO US Equity:PX_LAST", freq="ME")
            .pct_change()
            .iloc[-13:]
            * 100,
            "China": Series("MCHI US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "India": Series("INDA US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Brazil": Series("EWZ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Taiwan": Series("EWT US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
            * 100,
            "Vietnam": Series("VNM US Equity:PX_LAST", freq="ME")
            .pct_change()
            .iloc[-13:]
            * 100,
        }

        global_df = pd.DataFrame(global_data).T
        global_df.columns = [col.strftime("%b %Y") for col in global_df.columns]
        global_df = global_df.round(2)

        # Add global markets section to PDF
        story.append(
            Paragraph("Global Markets Monthly Performance (USD)", styles["Heading2"])
        )
        story.append(Spacer(1, 12))

        # Create table data for PDF (show last 6 months to fit on page)
        recent_months = global_df.columns[-6:]  # Last 6 months
        pdf_table_data = [["Market"] + list(recent_months)]

        for market in global_df.index:
            row = [market]
            for month in recent_months:
                row.append(f"{global_df.loc[market, month]:.2f}%")
            pdf_table_data.append(row)

        global_table = Table(pdf_table_data)
        global_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                ]
            )
        )

        story.append(global_table)

    except Exception as e:
        # If global markets data fails, just continue without it
        story.append(Paragraph("Global Markets data not available", styles["Normal"]))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    # Clean up temp file after PDF is built
    if tmp_file_path and os.path.exists(tmp_file_path):
        try:
            os.unlink(tmp_file_path)
        except (OSError, PermissionError):
            # If we can't delete it immediately, try to delete it later
            import atexit

            atexit.register(
                lambda: (
                    os.unlink(tmp_file_path) if os.path.exists(tmp_file_path) else None
                )
            )

    return buffer


# Load data
try:
    ff, fe = load_data()

    # Calculate the weekly percentage change
    weekly_pct_change = (
        fe.sum(axis=1).resample("W-Fri").last().pct_change(int(52)).loc["2007":]
    )

    # Create Plotly figure
    fig = go.Figure()

    # Add the main line
    fig.add_trace(
        go.Scatter(
            x=weekly_pct_change.index,
            y=weekly_pct_change.values * 100,  # Convert to percentage
            mode="lines",
            name="Weekly CAPEX % Change (52-week)",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + "<b>% Change:</b> %{y:.2f}%<br>"
            + "<extra></extra>",
        )
    )

    # Update layout
    fig.update_layout(
        title={
            "text": "Tech Companies CAPEX - 52-Week Percentage Change",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20},
        },
        xaxis_title="Date",
        yaxis_title="Percentage Change (%)",
        hovermode="x unified",
        template="plotly_white",
        height=600,
        showlegend=True,
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Display the chart
    st.plotly_chart(fig, width="stretch")

    # Add some statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Current % Change",
            (
                f"{weekly_pct_change.iloc[-1]*100:.2f}%"
                if len(weekly_pct_change) > 0
                else "N/A"
            ),
        )

    with col2:
        st.metric(
            "Max % Change",
            (
                f"{weekly_pct_change.max()*100:.2f}%"
                if len(weekly_pct_change) > 0
                else "N/A"
            ),
        )

    with col3:
        st.metric(
            "Min % Change",
            (
                f"{weekly_pct_change.min()*100:.2f}%"
                if len(weekly_pct_change) > 0
                else "N/A"
            ),
        )

    # PDF Download section
    st.subheader("📄 Download Report")
    st.markdown(
        "Generate and download a comprehensive PDF report with the chart and data."
    )

    if st.button("📥 Download PDF Report", type="primary"):
        try:
            with st.spinner("Generating PDF report..."):
                pdf_buffer = generate_pdf_report(fig, weekly_pct_change, ff, fe)

                # Create download button
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_buffer.getvalue(),
                    file_name=f"tech_capex_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    type="primary",
                )

                st.success(
                    "PDF report generated successfully! Click the download button above to save it."
                )

        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            st.info(
                "Make sure you have the required dependencies installed: pip install reportlab kaleido matplotlib"
            )

    # Global Markets Monthly Performance Table
    st.subheader("🌍 Global Markets Monthly Performance (USD)")
    st.markdown("Monthly percentage changes for major global equity markets")

    # Global markets data
    @st.cache_data
    def load_global_markets_data():
        try:
            global_data = {
                "ACWI": Series("ACWI US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "US": Series("SPY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "DM ex US": Series("IDEV US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "U.K.": Series("EWU US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "EAFE": Series("EFA US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Europe": Series("FEZ US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Germany": Series("EWG US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Japan": Series("EWJ US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Korea": Series("EWY US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Australia": Series("EWA US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Emerging": Series("VWO US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "China": Series("MCHI US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "India": Series("INDA US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Brazil": Series("EWZ US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Taiwan": Series("EWT US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Vietnam": Series("VNM US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
            }

            # Create DataFrame and transpose
            df = pd.DataFrame(global_data).T
            df.index.name = "Market"

            # Format dates as month-year
            df.columns = [col.strftime("%b %Y") for col in df.columns]

            # Round to 2 decimal places
            df = df.round(2)

            return df

        except Exception as e:
            st.error(f"Error loading global markets data: {str(e)}")
            return None

    # Load and display global markets data
    global_markets_df = load_global_markets_data()

    if global_markets_df is not None:
        # Display the table with custom styling
        st.dataframe(global_markets_df, width="stretch", use_container_width=True)

        # Add summary statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Best Performer (Latest Month)",
                f"{global_markets_df.iloc[:, -1].idxmax()}: {global_markets_df.iloc[:, -1].max():.2f}%",
            )

        with col2:
            st.metric(
                "Worst Performer (Latest Month)",
                f"{global_markets_df.iloc[:, -1].idxmin()}: {global_markets_df.iloc[:, -1].min():.2f}%",
            )

        with col3:
            avg_performance = global_markets_df.iloc[:, -1].mean()
            st.metric("Average Performance (Latest Month)", f"{avg_performance:.2f}%")
    else:
        st.info("Global markets data is not available. Please check your data sources.")

    # Major Indices Performance Table
    st.subheader("📈 Major Indices Monthly Performance")
    st.markdown("Monthly percentage changes for major global stock indices")

    @st.cache_data
    def load_major_indices_data():
        try:
            indices_data = {
                "S&P500": Series("SPX Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "Nasdaq": Series("CCMP Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "DJI30": Series("INDU Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "Russell2": Series("RTY Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "EuroStoxx50": Series("SX5E Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "FTSE100": Series("UKX Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "DAX": Series("DAX Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "CAC40": Series("CAC Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "Nikkie225": Series("NKY Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "TOPIX": Series("TPX Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "KOSPI": Series("KOSPI Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Nifty": Series("NIFTY Index:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "HSI": Series("HSI Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "SH": Series("SHCOMP Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
            }

            df = pd.DataFrame(indices_data).T
            df.index.name = "Index"
            df.columns = [col.strftime("%b %Y") for col in df.columns]
            df = df.round(2)
            return df

        except Exception as e:
            st.error(f"Error loading major indices data: {str(e)}")
            return None

    indices_df = load_major_indices_data()
    if indices_df is not None:
        st.dataframe(indices_df, width="stretch", use_container_width=True)
    else:
        st.info("Major indices data is not available.")

    # Sectors Performance Table
    st.subheader("🏭 Sectors Monthly Performance")
    st.markdown("Monthly percentage changes for S&P 500 sector ETFs")

    @st.cache_data
    def load_sectors_data():
        try:
            sectors_data = {
                "InfoTech": Series("XLK US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Industrials": Series("XLI US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Financials": Series("XLF US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Comm": Series("XLC US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "RealEstate": Series("XLRE US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Energy": Series("XLE US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Discretionary": Series("XLY US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Materials": Series("XLB US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "HealthCare": Series("XLV US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Staples": Series("XLP US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Utilities": Series("XLU US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
            }

            df = pd.DataFrame(sectors_data).T
            df.index.name = "Sector"
            df.columns = [col.strftime("%b %Y") for col in df.columns]
            df = df.round(2)
            return df

        except Exception as e:
            st.error(f"Error loading sectors data: {str(e)}")
            return None

    sectors_df = load_sectors_data()
    if sectors_df is not None:
        st.dataframe(sectors_df, width="stretch", use_container_width=True)
    else:
        st.info("Sectors data is not available.")

    # Thematic ETFs Performance Table
    st.subheader("🚀 Thematic ETFs Monthly Performance")
    st.markdown("Monthly percentage changes for thematic and specialized ETFs")

    @st.cache_data
    def load_thematic_data():
        try:
            thematic_data = {
                "FinTech": Series("FINX US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Real Estate": Series("VNQ US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Pave": Series("PAVE US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Space": Series("UFO US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Data/Infra": Series("SRVR US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "IoT": Series("SNSR US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "EV/Drive": Series("DRIV US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Pharma": Series("PPH US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Cloud": Series("SKYY US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Lit/Battery": Series("LIT US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Solar": Series("TAN US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Semis": Series("SOXX US Equity:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
            }

            df = pd.DataFrame(thematic_data).T
            df.index.name = "Thematic ETF"
            df.columns = [col.strftime("%b %Y") for col in df.columns]
            df = df.round(2)
            return df

        except Exception as e:
            st.error(f"Error loading thematic ETFs data: {str(e)}")
            return None

    thematic_df = load_thematic_data()
    if thematic_df is not None:
        st.dataframe(thematic_df, width="stretch", use_container_width=True)
    else:
        st.info("Thematic ETFs data is not available.")

    # Currencies Performance Table
    st.subheader("💱 Currencies Monthly Performance")
    st.markdown("Monthly percentage changes for major currencies (vs USD)")

    @st.cache_data
    def load_currencies_data():
        try:
            currencies_data = {
                "DXY": Series("DXY Index:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "EUR": -Series("USDEUR Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "GBP": -Series("USDGBP Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "JPY": -Series("USDJPY Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "KRW": -Series("USDKRW Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "AUD": -Series("USDAUD Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "INR": -Series("USDINR Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
            }

            df = pd.DataFrame(currencies_data).T
            df.index.name = "Currency"
            df.columns = [col.strftime("%b %Y") for col in df.columns]
            df = df.round(2)
            return df

        except Exception as e:
            st.error(f"Error loading currencies data: {str(e)}")
            return None

    currencies_df = load_currencies_data()
    if currencies_df is not None:
        st.dataframe(currencies_df, width="stretch", use_container_width=True)
    else:
        st.info("Currencies data is not available.")

    # Commodities Performance Table
    st.subheader("🥇 Commodities Monthly Performance")
    st.markdown("Monthly percentage changes for major commodities")

    @st.cache_data
    def load_commodities_data():
        try:
            commodities_data = {
                "Gold": Series("GOLDCOMP:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "Silver": Series("SLVR Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Crude": Series("WTI Comdty:PX_LAST", freq="ME").pct_change().iloc[-13:]
                * 100,
                "Copper": Series("HG1 Comdty:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
                "Bitcoin": Series("XBTUSD Curncy:PX_LAST", freq="ME")
                .pct_change()
                .iloc[-13:]
                * 100,
            }

            df = pd.DataFrame(commodities_data).T
            df.index.name = "Commodity"
            df.columns = [col.strftime("%b %Y") for col in df.columns]
            df = df.round(2)
            return df

        except Exception as e:
            st.error(f"Error loading commodities data: {str(e)}")
            return None

    commodities_df = load_commodities_data()
    if commodities_df is not None:
        st.dataframe(commodities_df, width="stretch", use_container_width=True)
    else:
        st.info("Commodities data is not available.")

    # Data table
    st.subheader("📈 Raw Data")
    st.dataframe(
        weekly_pct_change.tail(20).to_frame("52-Week % Change"),
        width="stretch",
    )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please make sure you have the required data sources available.")
