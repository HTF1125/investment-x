"""
Configuration settings for the Dash application
"""

# Define universe configurations based on your specifications
UNIVERSES = {
    "Major Indices": [
        {"code": "SPX Index", "name": "S&P500"},
        {"code": "CCMP Index", "name": "Nasdaq"},
        {"code": "INDU Index", "name": "DJI30"},
        {"code": "RTY Index", "name": "Russell2"},
        {"code": "SX5E Index", "name": "EuroStoxx50"},
        {"code": "UKX Index", "name": "FTSE100"},
        {"code": "DAX Index", "name": "DAX"},
        {"code": "CAC Index", "name": "CAC40"},
        {"code": "NKY Index", "name": "Nikkie225"},
        {"code": "TPX Index", "name": "TOPIX"},
        {"code": "KOSPI Index", "name": "KOSPI"},
        {"code": "NIFTY Index", "name": "Nifty"},
        {"code": "HSI Index", "name": "HSI"},
        {"code": "SHCOMP Index", "name": "SH"},
    ],
    "Sectors": [
        {"code": "XLK US Equity", "name": "InfoTech"},
        {"code": "XLI US Equity", "name": "Industrials"},
        {"code": "XLF US Equity", "name": "Financials"},
        {"code": "XLC US Equity", "name": "Comm"},
        {"code": "XLRE US Equity", "name": "RealEstate"},
        {"code": "XLE US Equity", "name": "Energy"},
        {"code": "XLY US Equity", "name": "Discretionary"},
        {"code": "XLB US Equity", "name": "Materials"},
        {"code": "XLV US Equity", "name": "HealthCare"},
        {"code": "XLP US Equity", "name": "Staples"},
        {"code": "XLU US Equity", "name": "Utilities"},
    ],
    "Themes": [
        {"code": "FINX US Equity", "name": "FinTech"},
        {"code": "VNQ US Equity", "name": "Real Estate"},
        {"code": "PAVE US Equity", "name": "Pave"},
        {"code": "UFO US Equity", "name": "Space"},
        {"code": "SRVR US Equity", "name": "Data/Infra"},
        {"code": "SNSR US Equity", "name": "IoT"},
        {"code": "DRIV US Equity", "name": "EV/Drive"},
        {"code": "PPH US Equity", "name": "Pharma"},
        {"code": "SKYY US Equity", "name": "Cloud"},
        {"code": "LIT US Equity", "name": "Lit/Battery"},
        {"code": "TAN US Equity", "name": "Solar"},
        {"code": "SOXX US Equity", "name": "Semis"},
    ],
    "Global Markets": [
        {"code": "ACWI US Equity", "name": "ACWI"},
        {"code": "SPY US Equity", "name": "US"},
        {"code": "IDEV US Equity", "name": "DM ex US"},
        {"code": "EWU US Equity", "name": "U.K."},
        {"code": "EFA US Equity", "name": "EAFE"},
        {"code": "FEZ US Equity", "name": "Europe"},
        {"code": "EWG US Equity", "name": "Germany"},
        {"code": "EWJ US Equity", "name": "Japan"},
        {"code": "EWY US Equity", "name": "Korea"},
        {"code": "EWA US Equity", "name": "Australia"},
        {"code": "VWO US Equity", "name": "Emerging"},
        {"code": "MCHI US Equity", "name": "China"},
        {"code": "INDA US Equity", "name": "India"},
        {"code": "EWZ US Equity", "name": "Brazil"},
        {"code": "EWT US Equity", "name": "Taiwan"},
        {"code": "VNM US Equity", "name": "Vietnam"},
    ],
    "Commodities": [
        {"code": "GC1 Comdty", "name": "Gold"},
        {"code": "SI1 Comdty", "name": "Silver"},
        {"code": "WTI Comdty", "name": "Curde"},
        {"code": "HG1 Comdty", "name": "Copper"},
        {"code": "XBTUSD Curncy", "name": "Bitcoin"},
    ],
}

# Frequency options
FREQUENCY_OPTIONS = [
    {"label": "📅 Daily", "value": "B"},
    {"label": "📊 Weekly", "value": "W-Fri"},
    {"label": "📈 Monthly", "value": "ME"},
    {"label": "🗓️ Yearly", "value": "YE"},
]

# Universe icons
UNIVERSE_ICONS = {
    "Major Indices": "🌍",
    "Sectors": "🏢",
    "Themes": "🚀",
    "Global Markets": "🗺️",
    "Commodities": "💰",
}

# App configuration
APP_CONFIG = {
    "title": "Global Market Returns",
    "description": "Real-time performance across major asset classes",
    "default_frequency": "ME",
    "capex_chart_height": 500,
}

# Styling configuration
COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#10b981",
    "success_light": "#d1fae5",
    "success_text": "#065f46",
    "danger": "#ef4444",
    "danger_light": "#fecaca",
    "danger_text": "#7f1d1d",
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "table_bg": "#f9fafb",
    "border": "#e2e8f0",
}

# CSS Styles
CUSTOM_CSS = """
body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
}

.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dash-spreadsheet-inner table tbody tr:hover {
    background-color: #f3f4f6 !important;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Chart container improvements */
.dash-graph {
    margin-bottom: 20px !important;
}

.dash-graph .js-plotly-plot {
    margin: 0 auto !important;
}

/* Ensure proper spacing for legends */
.plotly .legend {
    margin-top: 10px !important;
}
"""
