"""SEC EDGAR 13-F institutional holdings collector.

Fetches quarterly 13-F filings from SEC EDGAR for tracked institutional investors.
Parses XML holdings tables and stores in InstitutionalHolding model.
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, date

import requests

from ix.collectors.base import BaseCollector
from ix.db.conn import Session
from ix.db.models.institutional_holding import InstitutionalHolding


class SEC13FCollector(BaseCollector):
    name = "sec_13f"
    display_name = "SEC 13-F Holdings"
    schedule = "0 8 * * 1"  # Monday 8 AM (weekly check for new filings)
    category = "filings"

    TRACKED_FUNDS = {
        "0001350694": "BRIDGEWATER ASSOCIATES LP",
        "0001037389": "RENAISSANCE TECHNOLOGIES LLC",
        "0001067983": "BERKSHIRE HATHAWAY INC",
        "0001336528": "CITADEL ADVISORS LLC",
        "0001273087": "DE SHAW & CO LP",
        "0001061768": "TWO SIGMA INVESTMENTS LP",
        "0001582202": "MILLENNIUM MANAGEMENT LLC",
        "0001649339": "POINT72 ASSET MANAGEMENT LP",
        "0001040273": "BAUPOST GROUP LLC/MA",
        "0000921669": "DUQUESNE FAMILY OFFICE LLC",
        "0000902219": "SOROS FUND MANAGEMENT LLC",
        "0001345471": "PERSHING SQUARE CAPITAL MANAGEMENT LP",
        "0001167557": "APPALOOSA MANAGEMENT LP",
        "0001364742": "GREENLIGHT CAPITAL INC",
        "0000895421": "OAKTREE CAPITAL MANAGEMENT LP",
    }

    HEADERS = {
        "User-Agent": "Investment-X Research Platform admin@investment-x.com",
        "Accept-Encoding": "gzip, deflate",
    }

    EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
    EDGAR_FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0
        total = len(self.TRACKED_FUNDS)
        current = 0

        with Session() as db:
            for cik, fund_name in self.TRACKED_FUNDS.items():
                current += 1
                if progress_cb:
                    progress_cb(current, total, f"Checking {fund_name}")

                try:
                    count = self._fetch_fund_filings(db, cik, fund_name)
                    inserted += count
                except Exception as e:
                    self.logger.error(f"Error processing {fund_name} ({cik}): {e}")
                    errors += 1

                time.sleep(0.2)  # SEC rate limit: 10 req/sec

        self.update_state(last_data_date=str(date.today()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"13-F: {inserted} holdings from {total} funds, {errors} errors",
        }

    def _fetch_fund_filings(self, db, cik: str, fund_name: str) -> int:
        """Fetch recent 13-F filings for a specific fund."""
        # Use EDGAR full-text search API
        url = f"https://efts.sec.gov/LATEST/search-index?q=%2213-F%22&dateRange=custom&startdt=2024-01-01&forms=13-F-HR&entityName={cik}"

        # Simpler approach: use the EDGAR submissions API
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        try:
            resp = requests.get(submissions_url, headers=self.HEADERS, timeout=30)
            if resp.status_code != 200:
                self.logger.warning(f"EDGAR submissions fetch failed for {cik}: {resp.status_code}")
                return 0

            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            filing_dates = recent.get("filingDate", [])
            report_dates = recent.get("reportDate", [])

            count = 0
            for i, form in enumerate(forms):
                if form != "13-F-HR":
                    continue

                accession = accessions[i].replace("-", "")
                accession_display = accessions[i]
                filed = filing_dates[i] if i < len(filing_dates) else None
                report = report_dates[i] if i < len(report_dates) else None

                # Check if we already have this filing
                existing = db.query(InstitutionalHolding).filter(
                    InstitutionalHolding.accession_number.like(f"{accession_display}%")
                ).first()
                if existing:
                    continue

                # Fetch and parse the filing
                try:
                    holdings = self._parse_13f_filing(cik, accession, accession_display)
                    for holding in holdings:
                        h = InstitutionalHolding(
                            cik=cik,
                            fund_name=fund_name,
                            accession_number=f"{accession_display}_{holding.get('cusip', '')}",
                            report_date=datetime.strptime(report, "%Y-%m-%d").date() if report else date.today(),
                            filed_date=datetime.strptime(filed, "%Y-%m-%d").date() if filed else None,
                            cusip=holding.get("cusip"),
                            symbol=holding.get("symbol"),
                            security_name=holding.get("name", "Unknown"),
                            security_class=holding.get("class"),
                            shares=holding.get("shares", 0),
                            value_usd=holding.get("value", 0),
                            put_call=holding.get("put_call"),
                            meta={"accession": accession_display},
                        )
                        db.add(h)
                        count += 1

                    if count > 0 and count % 50 == 0:
                        db.flush()

                    time.sleep(0.2)
                except Exception as e:
                    self.logger.warning(f"Failed to parse filing {accession_display}: {e}")

                # Only process recent filings (last 2 quarters)
                if count > 2000:
                    break

            return count

        except Exception as e:
            self.logger.error(f"Failed to fetch submissions for {cik}: {e}")
            return 0

    def _parse_13f_filing(self, cik: str, accession: str, accession_display: str) -> list:
        """Parse a 13-F XML information table."""
        # Try to find the XML info table
        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/"

        try:
            resp = requests.get(index_url, headers=self.HEADERS, timeout=30)
            if resp.status_code != 200:
                return []

            # Find the information table XML file
            xml_url = None
            for line in resp.text.split("\n"):
                lower = line.lower()
                if "infotable" in lower and ".xml" in lower:
                    # Extract filename from the index page
                    import re
                    match = re.search(r'href="([^"]*infotable[^"]*\.xml)"', lower)
                    if match:
                        xml_url = index_url + match.group(1)
                        break

            if not xml_url:
                # Try common naming patterns
                for suffix in ["infotable.xml", "primary_doc.xml"]:
                    test_url = f"{index_url}{suffix}"
                    test_resp = requests.head(test_url, headers=self.HEADERS, timeout=10)
                    if test_resp.status_code == 200:
                        xml_url = test_url
                        break
                    time.sleep(0.1)

            if not xml_url:
                return []

            time.sleep(0.1)
            xml_resp = requests.get(xml_url, headers=self.HEADERS, timeout=30)
            if xml_resp.status_code != 200:
                return []

            return self._parse_info_table_xml(xml_resp.text)

        except Exception as e:
            self.logger.warning(f"Failed to parse 13-F: {e}")
            return []

    def _parse_info_table_xml(self, xml_text: str) -> list:
        """Parse 13-F information table XML into a list of holdings."""
        holdings = []
        try:
            # Handle namespace
            xml_text = xml_text.replace('xmlns=', 'xmlns_orig=')
            root = ET.fromstring(xml_text)

            for entry in root.iter():
                if "infotable" in entry.tag.lower():
                    holding = {}
                    for child in entry:
                        tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                        text = (child.text or "").strip()

                        if "nameofissuer" in tag:
                            holding["name"] = text
                        elif "cusip" in tag:
                            holding["cusip"] = text
                        elif "value" in tag and "ssh" not in tag:
                            try:
                                holding["value"] = int(text)
                            except ValueError:
                                pass
                        elif "sshprnamt" in tag:
                            try:
                                holding["shares"] = int(text)
                            except ValueError:
                                pass
                        elif "sshprnamttype" in tag:
                            holding["class"] = text
                        elif "putcall" in tag:
                            holding["put_call"] = text

                    if holding.get("name"):
                        holdings.append(holding)

        except ET.ParseError as e:
            self.logger.warning(f"XML parse error: {e}")

        return holdings
