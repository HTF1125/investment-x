"""
Data loading utilities for market data
"""
import pandas as pd
from ix import Series


def get_universe_data(universe_name, assets, freq="ME"):
    """Get data for a specific universe with specified frequency"""
    try:
        df = pd.DataFrame(
            {
                asset["name"] or asset["code"]: Series(f"{asset['code']}:PX_LAST")
                for asset in assets
            }
        )
        return (
            df.ffill().resample(freq).last().pct_change(fill_method=None).mul(100).round(2).iloc[-13:]
        )
    except Exception as e:
        print(f"Error loading {universe_name}: {e}")
        return pd.DataFrame()


def get_data_with_frequency(universes, freq="ME"):
    """Get data for all universes with specified frequency"""
    universe_data = {}

    for universe_name, assets in universes.items():
        df = get_universe_data(universe_name, assets, freq)
        if not df.empty:
            # Format index based on frequency
            if freq == "YE":
                df.index = df.index.strftime("%Y")
            elif freq == "ME":
                df.index = df.index.strftime("%y-%m")
            elif freq == "W-Fri":
                df.index = df.index.strftime("%y-%m-%d")
            else:  # Daily
                df.index = df.index.strftime("%y-%m-%d")

            df = df.T
            df.index.name = "Asset"
            df = df.reset_index()
            universe_data[universe_name] = df.to_dict(orient="records")

    return universe_data


def load_global_markets_data():
    """Load global markets data"""
    try:
        global_data = {
            "ACWI": Series("ACWI US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "US": Series("SPY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "DM ex US": Series("IDEV US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "U.K.": Series("EWU US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "EAFE": Series("EFA US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Europe": Series("FEZ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Germany": Series("EWG US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Japan": Series("EWJ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Korea": Series("EWY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Australia": Series("EWA US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Emerging": Series("VWO US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "China": Series("MCHI US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "India": Series("INDA US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Brazil": Series("EWZ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Taiwan": Series("EWT US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Vietnam": Series("VNM US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
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
        print(f"Error loading global markets data: {str(e)}")
        return None


def load_major_indices_data():
    """Load major indices data"""
    try:
        indices_data = {
            "S&P500": Series("SPX Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Nasdaq": Series("CCMP Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "DJI30": Series("INDU Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Russell2": Series("RTY Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "EuroStoxx50": Series("SX5E Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "FTSE100": Series("UKX Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "DAX": Series("DAX Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "CAC40": Series("CAC Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Nikkie225": Series("NKY Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "TOPIX": Series("TPX Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "KOSPI": Series("KOSPI Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Nifty": Series("NIFTY Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "HSI": Series("HSI Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "SH": Series("SHCOMP Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
        }

        df = pd.DataFrame(indices_data).T
        df.index.name = "Index"
        df.columns = [col.strftime("%b %Y") for col in df.columns]
        df = df.round(2)
        return df

    except Exception as e:
        print(f"Error loading major indices data: {str(e)}")
        return None


def load_sectors_data():
    """Load sectors data"""
    try:
        sectors_data = {
            "InfoTech": Series("XLK US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Industrials": Series("XLI US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Financials": Series("XLF US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Comm": Series("XLC US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "RealEstate": Series("XLRE US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Energy": Series("XLE US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Discretionary": Series("XLY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Materials": Series("XLB US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "HealthCare": Series("XLV US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Staples": Series("XLP US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Utilities": Series("XLU US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
        }

        df = pd.DataFrame(sectors_data).T
        df.index.name = "Sector"
        df.columns = [col.strftime("%b %Y") for col in df.columns]
        df = df.round(2)
        return df

    except Exception as e:
        print(f"Error loading sectors data: {str(e)}")
        return None


def load_thematic_data():
    """Load thematic ETFs data"""
    try:
        thematic_data = {
            "FinTech": Series("FINX US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Real Estate": Series("VNQ US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Pave": Series("PAVE US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Space": Series("UFO US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Data/Infra": Series("SRVR US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "IoT": Series("SNSR US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "EV/Drive": Series("DRIV US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Pharma": Series("PPH US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Cloud": Series("SKYY US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Lit/Battery": Series("LIT US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Solar": Series("TAN US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Semis": Series("SOXX US Equity:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
        }

        df = pd.DataFrame(thematic_data).T
        df.index.name = "Thematic ETF"
        df.columns = [col.strftime("%b %Y") for col in df.columns]
        df = df.round(2)
        return df

    except Exception as e:
        print(f"Error loading thematic ETFs data: {str(e)}")
        return None


def load_currencies_data():
    """Load currencies data"""
    try:
        currencies_data = {
            "DXY": Series("DXY Index:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "EUR": -Series("USDEUR Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "GBP": -Series("USDGBP Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "JPY": -Series("USDJPY Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "KRW": -Series("USDKRW Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "AUD": -Series("USDAUD Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "INR": -Series("USDINR Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
        }

        df = pd.DataFrame(currencies_data).T
        df.index.name = "Currency"
        df.columns = [col.strftime("%b %Y") for col in df.columns]
        df = df.round(2)
        return df

    except Exception as e:
        print(f"Error loading currencies data: {str(e)}")
        return None


def load_commodities_data():
    """Load commodities data"""
    try:
        commodities_data = {
            "Gold": Series("GOLDCOMP:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Silver": Series("SLVR Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Crude": Series("WTI Comdty:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Copper": Series("HG1 Comdty:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
            "Bitcoin": Series("XBTUSD Curncy:PX_LAST", freq="ME").pct_change().iloc[-13:] * 100,
        }

        df = pd.DataFrame(commodities_data).T
        df.index.name = "Commodity"
        df.columns = [col.strftime("%b %Y") for col in df.columns]
        df = df.round(2)
        return df

    except Exception as e:
        print(f"Error loading commodities data: {str(e)}")
        return None