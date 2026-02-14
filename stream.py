import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ix.db.query import Series
from ix.cht.technical import ElliottWave

# Page Config
st.set_page_config(layout="wide", page_title="Elliott Wave Test")

st.title("📈 Antigravity: Elliott Wave Test")


# 1. Get Data & Cache
@st.cache_data(ttl=3600)
def fetch_data(ticker: str):
    """
    Fetch series data and cache it.
    """
    try:
        # Fetch using internal query engine
        s = Series(ticker)

        # If empty, it might be because of missing DB entry.
        # Additional handling or fallback could be added here.
        if s.empty:
            return None

        # Ensure it's a DataFrame for consistency if needed, but Series is fine.
        return s
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None


TICKER = "SPX Index:PX_LAST"

# Sidebar
st.sidebar.header("Configuration")
selected_ticker = st.sidebar.text_input("Ticker", value=TICKER)

if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()

# Fetch
st.subheader(f"1. Data: {selected_ticker}")
data = fetch_data(selected_ticker)

if data is not None and not data.empty:
    st.write(f"Loaded {len(data)} rows.")
    # Rename for Streamlit/Altair compatibility
    chart_data = data.to_frame() if isinstance(data, pd.Series) else data.copy()
    chart_data.columns = [str(c).replace(":", "_") for c in chart_data.columns]

    st.line_chart(chart_data)

    # 2. Test Elliott Wave
    st.subheader("2. Elliott Wave Analysis")

    # We cache the chart generation as well since it involves calculation
    @st.cache_data(ttl=3600)
    def generate_ew_chart(ticker_symbol):
        return ElliottWave(ticker_symbol)

    try:
        with st.spinner("Calculating Elliott Waves..."):
            fig = generate_ew_chart(selected_ticker)
            st.plotly_chart(fig, use_container_width=True, height=800)
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        st.warning(
            "Note: ElliottWave function expects the ticker to exist in the database and returning valid OHLC-ish data (or close price)."
        )

else:
    st.warning(
        f"No data found for {selected_ticker}. Please ensure the ticker exists in the database."
    )
