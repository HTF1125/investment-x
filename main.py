import streamlit as st
from ix.core.tech import BollingerBand, RSI
from datetime import datetime, timedelta

st.set_page_config(
    layout="wide",
    page_title="InvestmentX",
    page_icon="📊",
)


@st.cache_data(ttl=60 * 60)
def get_bollingerband(asset: str) -> BollingerBand:
    return BollingerBand.from_meta(asset)


@st.cache_data(ttl=60 * 60)
def get_rsi(asset: str) -> RSI:
    return RSI.from_meta(asset)


# Sidebar for user inputs
st.sidebar.title("Settings")
asset = st.sidebar.selectbox("Select Asset", ["IAU"], index=0)

# Date range selection
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365)  # Default to 1 year of data

# Main content
st.title(f"{asset} Technical Analysis Dashboard")

# Metrics
bb = get_bollingerband(asset)
rsi = get_rsi(asset)

col1, col2, col3 = st.columns(3)
with col1:
    current_price = bb.px.iloc[-1]
    st.metric(
        "Current Price", f"${current_price:.2f}", f"{bb.px.pct_change().iloc[-1]:.2%}"
    )

with col2:
    current_rsi = rsi.rsi.iloc[-1]
    st.metric("Current RSI", f"{current_rsi:.2f}")

with col3:
    r = (
        (bb.px.iloc[-1] - bb.middle.iloc[-1])
        / (bb.upper.iloc[-1] - bb.lower.iloc[-1])
        * 2
    )
    st.metric("Bollinger Band Position", f"{r:.2f}")

# Charts
tab1, tab2 = st.tabs(["Bollinger Bands", "RSI"])

with tab1:
    st.plotly_chart(bb.plot(start=str(start_date)), use_container_width=True)

with tab2:
    st.plotly_chart(rsi.plot(start=str(start_date)), use_container_width=True)

# Footer
st.sidebar.markdown("---")


import pandas as pd
from ix.db import Metadata
from typing import List


@st.cache_data(ttl=60 * 60)
def get_metadata() -> List[Metadata]:
    st.write("get_metadata called.")
    return Metadata.find_all(projection_model=Metadata).run()


data = pd.DataFrame([metadata.model_dump() for metadata in get_metadata()])
