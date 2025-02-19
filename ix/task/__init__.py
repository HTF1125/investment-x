import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_fred_data
from ix.misc import get_logger
from ix import misc
from ix.db import Metadata
import ix
import io

logger = get_logger(__name__)


def run():
    update_px_last()


def get_performance(px_last: pd.Series) -> dict:
    px_last = px_last.resample("D").last().ffill()
    asofdate = pd.Timestamp(str(px_last.index[-1]))
    level = px_last.loc[asofdate]
    pct_chg = (level / px_last).sub(1).mul(100).round(2)
    out = {}
    for period in ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]:
        r_date = misc.get_relative_date(asofdate=asofdate, period=period)
        try:
            out[f"PCT_CHG_{period}"] = pct_chg.loc[r_date]
        except:
            pass
    return out


def update_px_last():
    logger.debug("Initialize update PX_LAST data")

    for metadata in Metadata.find_all().run():
        try:
            # Process Yahoo ticker data if available.
            if metadata.yah_ticker:
                metadata.update_px()

            # Process FRED ticker data if Yahoo ticker isn't available.
            elif metadata.fre_ticker:
                logger.info(
                    f"Processing FRED ticker for metadata code: {metadata.code}"
                )
                ts = get_fred_data(ticker=metadata.fre_ticker)

                if ts.empty:
                    logger.warning(
                        f"No FRED data returned for ticker {metadata.fre_ticker}"
                    )
                    continue

                # Assume the first column holds the required time series.
                ts_series = ts.iloc[:, 0].astype(float).round(4)
                metadata.ts(field="PX_LAST").data = ts_series
                logger.info(
                    f"Successfully updated PX_LAST for code: {metadata.code} using FRED data"
                )
                logger.debug(
                    f"FRED data tail for code {metadata.code}: {ts_series.tail().to_dict()}"
                )
            else:
                logger.warning(f"No ticker found for metadata code: {metadata.code}")

        except Exception as e:
            logger.error(
                f"Error processing metadata code {metadata.code}: {e}", exc_info=True
            )

    logger.debug("Timeseries update process completed.")


def update_economic_calendar():

    import investpy
    from ix.misc import as_date, onemonthbefore, onemonthlater
    from ix.db import EconomicCalendar
    import pandas as pd

    data = investpy.economic_calendar(
        from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
        to_date=as_date(onemonthlater(), "%d/%m/%Y"),
    )

    if not isinstance(data, pd.DataFrame):
        return
    data["date"] = pd.to_datetime(data["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    data = data.drop(columns=["id"])

    EconomicCalendar.delete_all()
    objs = []
    for record in data.to_dict("records"):
        record = {str(key): value for key, value in record.items()}
        objs.append(EconomicCalendar(**record))
    EconomicCalendar.insert_many(objs)


def bloomberg_only():

    import requests
    from ix.db import Metadata
    from ix.misc import get_bloomberg_data

    # Define the API URL and parameters
    url = "https://port-0-investmentx-ghdys32bls2zef7e.sel5.cloudtype.app"
    response = requests.get(f"{url}/api/metadatas")
    for metadata in response.json():
        mt = Metadata(**metadata)
        for data_source in mt.data_sources:
            if data_source.source == "BLOOMBERG":
                ts = get_bloomberg_data(
                    code=data_source.s_code,
                    field=data_source.s_field,
                ).iloc[:, 0]
                params = {"code": mt.code, "field": data_source.field}
                body = {"data": ts.to_dict()}
                requests.put(f"{url}/api/timeseries", params=params, json=body)
                # Check the response
                if response.status_code == 200:
                    print("Time series updated successfully.")
                else:
                    print(
                        f"Failed to update time series. Status code: {response.status_code}, Response: {response.text}"
                    )


def get_px_last() -> pd.DataFrame:

    datas = []
    for metadata in ix.db.Metadata.find_all().run():
        px_last = metadata.ts().data
        if px_last.empty:
            continue

        data = {
            "isin": metadata.id_isin,
            "code": metadata.code,
            "px_last": px_last.iloc[-1],
        }
        datas.append(data)
    px_last_latest = pd.DataFrame(datas).dropna()
    return px_last_latest


from typing import List
from ix.misc.email import EmailSender
from ix.misc.settings import Settings
from ix.misc.terminal import get_logger

logger = get_logger(__name__)

def send_px_last(
    recipients: List[str] = Settings.email_recipients,
    subject: str = "Daily PX Last Report",
    content: str = "Please find the attached CSV file with the latest PX data.",
    filename: str = "px_last.csv",
) -> bool:
    try:
        px_last = get_px_last()

        if px_last.empty:
            logger.warning("No data available in px_last. Email not sent.")
            return False

        email_sender = EmailSender(
            to=", ".join(recipients),
            subject=subject,
            content=content,
        )

        # Convert the DataFrame to a CSV in a BytesIO buffer.
        buffer = io.BytesIO()
        px_last.to_csv(buffer, index=False)
        buffer.seek(0)  # Reset the buffer's pointer to the beginning

        # Use the correct parameter name `file_buffer`
        email_sender.attach(file_buffer=buffer, filename=filename)
        email_sender.send()

        logger.info(f"Email sent successfully to {', '.join(recipients)}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


if __name__ == "__main__":
    success = send_px_last()
    print(f"Email sent successfully: {success}")
