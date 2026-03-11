"""Insider transaction collector via OpenInsider scraping.

Fetches recent insider purchases/sales and stores as NewsItem entries.
"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class InsiderTransactionCollector(BaseCollector):
    name = "insider_tx"
    display_name = "Insider Transactions"
    schedule = "0 21 * * 1-5"  # Weekdays 9 PM
    category = "filings"

    # OpenInsider provides a nice tabular view of SEC Form 4 filings
    BASE_URL = "http://openinsider.com/screener"
    PARAMS = {
        "s": "",
        "o": "",
        "pl": "",
        "ph": "",
        "ll": "",
        "lh": "",
        "fd": "7",  # Last 7 days
        "fdr": "",
        "td": "0",
        "tdr": "",
        "feession": "",
        "cession": "",
        "sid": "",
        "ta": "1",  # Only notable transactions
        "tc": "1",
        "p": "0",
        "q": "0",
        "cnt": "100",
    }

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        try:
            transactions = self._scrape_openinsider()
            if not transactions:
                self.update_state(error="No transactions found")
                return {"inserted": 0, "updated": 0, "errors": 0, "message": "No new transactions"}

            total = len(transactions)
            with Session() as db:
                for i, tx in enumerate(transactions):
                    if progress_cb and (i + 1) % 10 == 0:
                        progress_cb(i + 1, total, f"Processing {i + 1}/{total}")
                    try:
                        was_new = self._upsert_news_item(
                            db,
                            source="sec_edgar",
                            source_name="Insider Transaction",
                            title=self._format_title(tx),
                            url=tx.get("url"),
                            summary=self._format_summary(tx),
                            symbols=[tx["ticker"]] if tx.get("ticker") else [],
                            meta={
                                "insider_name": tx.get("insider_name"),
                                "insider_title": tx.get("insider_title"),
                                "company": tx.get("company"),
                                "ticker": tx.get("ticker"),
                                "transaction_type": tx.get("tx_type"),
                                "shares": tx.get("shares"),
                                "price": tx.get("price"),
                                "value": tx.get("value"),
                                "ownership_change": tx.get("ownership_change"),
                            },
                            published_at=tx.get("filing_date"),
                        )
                        if was_new:
                            inserted += 1
                    except Exception as e:
                        self.logger.error(f"Error inserting tx: {e}")
                        errors += 1

                    # Flush per-item to ensure dedup check sees prior inserts
                    try:
                        db.flush()
                    except Exception:
                        db.rollback()

            self.update_state(last_data_date=str(datetime.now().date()))

        except Exception as e:
            self.logger.exception(f"Insider tx collector failed: {e}")
            self.update_state(error=str(e))
            return {"inserted": 0, "updated": 0, "errors": 1, "message": str(e)}

        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"Insider Tx: {inserted} new transactions",
        }

    def _scrape_openinsider(self) -> list:
        """Scrape the OpenInsider screener page."""
        transactions = []
        try:
            resp = requests.get(self.BASE_URL, params=self.PARAMS, timeout=30)
            if resp.status_code != 200:
                self.logger.warning(f"OpenInsider returned {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", {"class": "tinytable"})
            if not table:
                self.logger.warning("No transaction table found on OpenInsider")
                return []

            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 12:
                    continue

                try:
                    filing_date = cells[1].get_text().strip()
                    trade_date = cells[2].get_text().strip()
                    ticker = cells[3].get_text().strip()
                    company = cells[4].get_text().strip()
                    insider_name = cells[5].get_text().strip()
                    insider_title = cells[6].get_text().strip()
                    tx_type = cells[7].get_text().strip()
                    price = cells[8].get_text().strip().replace("$", "").replace(",", "")
                    shares = cells[9].get_text().strip().replace(",", "").replace("+", "").replace("-", "")
                    value = cells[10].get_text().strip().replace("$", "").replace(",", "").replace("+", "").replace("-", "")
                    ownership_change = cells[11].get_text().strip()

                    # Build filing URL
                    link = cells[1].find("a")
                    href = link["href"] if link and link.get("href") else None
                    if href:
                        url = href if href.startswith("http") else f"https://openinsider.com{href}"
                    else:
                        url = None

                    tx = {
                        "filing_date": self._parse_date(filing_date),
                        "trade_date": trade_date,
                        "ticker": ticker,
                        "company": company,
                        "insider_name": insider_name,
                        "insider_title": insider_title,
                        "tx_type": tx_type,
                        "url": url,
                    }

                    try:
                        tx["price"] = float(price) if price else None
                    except ValueError:
                        tx["price"] = None
                    try:
                        tx["shares"] = int(shares) if shares else None
                    except ValueError:
                        tx["shares"] = None
                    try:
                        tx["value"] = int(value) if value else None
                    except ValueError:
                        tx["value"] = None
                    tx["ownership_change"] = ownership_change

                    transactions.append(tx)
                except Exception as e:
                    self.logger.warning(f"Failed to parse row: {e}")

        except Exception as e:
            self.logger.error(f"OpenInsider scrape failed: {e}")

        return transactions

    @staticmethod
    def _parse_date(s: str):
        """Parse date with or without time component."""
        if not s:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s.strip(), fmt)
            except ValueError:
                continue
        return None

    def _format_title(self, tx: dict) -> str:
        action = "bought" if "P" in (tx.get("tx_type") or "") else "sold"
        return f"{tx.get('insider_name', 'Unknown')} {action} {tx.get('ticker', '???')}"

    def _format_summary(self, tx: dict) -> str:
        parts = []
        if tx.get("insider_title"):
            parts.append(f"{tx['insider_title']} at {tx.get('company', '')}")
        if tx.get("shares") and tx.get("price"):
            parts.append(f"{tx['shares']:,} shares @ ${tx['price']:.2f}")
        if tx.get("value"):
            parts.append(f"Value: ${tx['value']:,}")
        return " | ".join(parts) if parts else ""
