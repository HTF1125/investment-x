"""
Daily Research PDF Fetcher
Searches for recent PDFs from top macro research sources using current
month/year terms for natural recency filtering, downloads them, and
uploads to Google Drive "0. Research" folder.

Dedup across runs ensures daily execution only fetches new content.

Usage:
    python scripts/fetch_research_pdfs.py --test              # discover only
    python scripts/fetch_research_pdfs.py                      # download + upload
    python scripts/fetch_research_pdfs.py --skip-upload        # download only, no Drive
    python scripts/fetch_research_pdfs.py --reset              # clear seen URLs and re-fetch
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

DRIVE_FOLDER_ID = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"

# Domain-to-issuer mapping
DOMAIN_MAP = {
    "blackrock.com": "BlackRock",
    "pimco.com": "PIMCO",
    "pgim.com": "PGIM",
    "franklintempleton.com": "Franklin-Templeton",
    "invesco.com": "Invesco",
    "nuveen.com": "Nuveen",
    "robeco.com": "Robeco",
    "schroders.com": "Schroders",
    "researchaffiliates.com": "Research-Affiliates",
    "oaktreecapital.com": "Oaktree",
    "aqr.com": "AQR",
    "man.com": "Man-Group",
    "crescat.net": "Crescat",
    "hussmanfunds.com": "Hussman",
    "bridgewater.com": "Bridgewater",
    "gmo.com": "GMO",
    "am.jpmorgan.com": "JPMorgan-AM",
    "jpmorgan.com": "JPMorgan",
    "goldmansachs.com": "Goldman-Sachs",
    "morganstanley.com": "Morgan-Stanley",
    "ubs.com": "UBS",
    "advisors.ubs.com": "UBS",
    "db.com": "Deutsche-Bank",
    "inside-research.db.com": "Deutsche-Bank",
    "equityview.research.db.com": "Deutsche-Bank",
    "barclays.com": "Barclays",
    "privatebank.barclays.com": "Barclays",
    "credit-suisse.com": "Credit-Suisse",
    "nomura.com": "Nomura",
    "hsbc.com": "HSBC",
    "bnpparibas.com": "BNP-Paribas",
    "federalreserve.gov": "Fed",
    "newyorkfed.org": "NY-Fed",
    "ecb.europa.eu": "ECB",
    "bis.org": "BIS",
    "imf.org": "IMF",
    "elibrary.imf.org": "IMF",
    "worldbank.org": "World-Bank",
    "documents1.worldbank.org": "World-Bank",
    "boj.or.jp": "BOJ",
    "bankofengland.co.uk": "BOE",
    "rba.gov.au": "RBA",
    "bok.or.kr": "BOK",
    "apolloacademy.com": "Apollo",
    "advisorperspectives.com": "Advisor-Perspectives",
    "yardeni.com": "Yardeni",
    "wisdomtree.com": "WisdomTree",
    "ark-invest.com": "ARK",
    "stlouisfed.org": "St-Louis-Fed",
    "news.research.stlouisfed.org": "St-Louis-Fed",
    "nber.org": "NBER",
    "ssrn.com": "SSRN",
    "mfs.com": "MFS",
    "russellinvestments.com": "Russell",
    "documents.nuveen.com": "Nuveen",
    # ── New — Hedge Funds / Quant Firms ──
    "deshaw.com": "DE-Shaw",
    "twosigma.com": "Two-Sigma",
    "citadel.com": "Citadel",
    "panteracapital.com": "Pantera",
    "crossbordercapital.com": "CrossBorder-Capital",
    "marathon-am.com": "Marathon-AM",
    # ── New — Korean ──
    "bok.or.kr": "BOK",
    "kdi.re.kr": "KDI",
    "securities.miraeasset.com": "Mirae-Asset",
    "samsungpop.com": "Samsung-Securities",
    "nhqv.com": "NH-Investment",
    # ── New — Academic / Policy ──
    "brookings.edu": "Brookings",
    "piie.com": "PIIE",
    "kansascityfed.org": "Kansas-City-Fed",
    "chicagofed.org": "Chicago-Fed",
    "frbsf.org": "SF-Fed",
    "bostonfed.org": "Boston-Fed",
    "philadelphiafed.org": "Philly-Fed",
    "clevelandfed.org": "Cleveland-Fed",
    "dallasfed.org": "Dallas-Fed",
    "minneapolisfed.org": "Minneapolis-Fed",
    "atlantafed.org": "Atlanta-Fed",
    "richmondfed.org": "Richmond-Fed",
    "troweprice.com": "T-Rowe-Price",
    "vanguard.com": "Vanguard",
    "capitaleconomics.com": "Capital-Economics",
    "oxfordeconomics.com": "Oxford-Economics",
    "lazardassetmanagement.com": "Lazard",
    "wellington.com": "Wellington",
    "ssga.com": "State-Street",
    "nb.com": "Neuberger-Berman",
    "alliancebernstein.com": "AllianceBernstein",
    "northerntrust.com": "Northern-Trust",
    "tcw.com": "TCW",
}

# Junk title patterns to skip
JUNK_PATTERNS = [
    r"procurement plan",
    r"prospectus",
    r"important information about benchmark",
    r"privacy policy",
    r"terms and conditions",
    r"cookie",
    r"disclaimer",
    r"annual report and audited",
    r"form\s+(?:adv|crs|n-)",
    r"proxy\s+statement",
    r"distribution schedule",
    r"dividend dates",
    r"consent (?:order|prohibition)",
    r"blackout period",
    r"iso\s*20022",
    r"100 per cent.*issue date",
    r"active etfs$",
    r"^the world bank$",
    r"^gmo\s+(?:trust|climate|emerging|horizons)",
    r"robeco climate global credits",
]
JUNK_RE = re.compile("|".join(JUNK_PATTERNS), re.IGNORECASE)


def build_queries() -> list[str]:
    """Build search queries using current month/year for natural recency.

    The key insight: using "March 2026" in queries naturally returns
    content from the current period. Combined with dedup across daily
    runs, this ensures we only get new content each day.
    """
    now = datetime.now()
    month_year = now.strftime("%B %Y")  # e.g., "March 2026"

    return [
        # ── Weekly market commentary (highest frequency) ──
        f'filetype:pdf weekly commentary {month_year} site:blackrock.com OR site:jpmorgan.com OR site:pimco.com OR site:goldmansachs.com',
        f'filetype:pdf weekly market update {month_year} site:ubs.com OR site:morganstanley.com OR site:barclays.com OR site:db.com',
        f'filetype:pdf weekly market {month_year} site:am.jpmorgan.com OR site:invesco.com OR site:nuveen.com OR site:schroders.com',

        # ── Macro / economic research ──
        f'filetype:pdf macro research {month_year} site:blackrock.com OR site:jpmorgan.com OR site:morganstanley.com OR site:ubs.com',
        f'filetype:pdf economic outlook {month_year} site:goldmansachs.com OR site:db.com OR site:barclays.com OR site:nomura.com',

        # ── Fixed income / credit ──
        f'filetype:pdf fixed income credit {month_year} site:pimco.com OR site:pgim.com OR site:nuveen.com OR site:franklintempleton.com',

        # ── Equity strategy ──
        f'filetype:pdf equity strategy {month_year} site:morganstanley.com OR site:goldmansachs.com OR site:jpmorgan.com OR site:ubs.com',

        # ── Central bank / policy research ──
        f'filetype:pdf {month_year} site:federalreserve.gov OR site:newyorkfed.org OR site:ecb.europa.eu OR site:bis.org',
        f'filetype:pdf {month_year} site:imf.org OR site:worldbank.org OR site:nber.org OR site:stlouisfed.org',

        # ── Independent / hedge fund research ──
        f'filetype:pdf research {month_year} site:apolloacademy.com OR site:yardeni.com OR site:advisorperspectives.com OR site:researchaffiliates.com',
        f'filetype:pdf {month_year} site:oaktreecapital.com OR site:crescat.net OR site:hussmanfunds.com OR site:aqr.com OR site:gmo.com',

        # ── Multi-asset / allocation ──
        f'filetype:pdf asset allocation {month_year} site:man.com OR site:robeco.com OR site:wisdomtree.com OR site:bridgewater.com',

        # ── Commodities & FX ──
        f'filetype:pdf commodities gold oil {month_year} site:goldmansachs.com OR site:jpmorgan.com OR site:ubs.com OR site:wisdomtree.com',
        f'filetype:pdf currency fx outlook {month_year} site:ubs.com OR site:db.com OR site:hsbc.com OR site:nomura.com',

        # ── Quant / Hedge fund research ──
        f'filetype:pdf research {month_year} site:deshaw.com OR site:twosigma.com OR site:citadel.com OR site:panteracapital.com',
        f'filetype:pdf market outlook {month_year} site:lazardassetmanagement.com OR site:wellington.com OR site:ssga.com OR site:nb.com',

        # ── Korean macro / research ──
        f'filetype:pdf macro outlook {month_year} site:bok.or.kr OR site:kdi.re.kr',
        f'filetype:pdf 시장전망 {month_year} site:securities.miraeasset.com OR site:samsungpop.com OR site:nhqv.com',

        # ── Regional Federal Reserve research ──
        f'filetype:pdf {month_year} site:kansascityfed.org OR site:chicagofed.org OR site:frbsf.org OR site:bostonfed.org',
        f'filetype:pdf {month_year} site:philadelphiafed.org OR site:clevelandfed.org OR site:dallasfed.org OR site:atlantafed.org',

        # ── Think tanks & academic ──
        f'filetype:pdf economic policy {month_year} site:brookings.edu OR site:piie.com OR site:nber.org',
        f'filetype:pdf outlook strategy {month_year} site:capitaleconomics.com OR site:oxfordeconomics.com OR site:troweprice.com',

        # ── Additional asset managers ──
        f'filetype:pdf weekly outlook {month_year} site:alliancebernstein.com OR site:northerntrust.com OR site:tcw.com OR site:vanguard.com',
    ]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PROGRESS_FILE = Path(__file__).parent / "_daily_pdf_progress.json"


def load_seen_urls():
    """Load previously downloaded URLs to avoid duplicates."""
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            return set(data.get("seen_urls", []))
        except Exception:
            pass
    return set()


def save_seen_urls(seen_urls):
    """Save seen URLs for dedup across runs."""
    data = {"seen_urls": list(seen_urls), "last_run": datetime.now().isoformat()}
    PROGRESS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _firecrawl_cmd():
    """Get firecrawl CLI command."""
    for cmd in [["npx", "firecrawl"], ["firecrawl"]]:
        try:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True, text=True, timeout=30,
                shell=(sys.platform == "win32"),
            )
            if result.returncode == 0:
                return cmd
        except Exception:
            pass
    return None


def search_pdfs_firecrawl(query, firecrawl_cmd, num_results=10):
    """Search for PDFs using Firecrawl search."""
    pdfs = []
    try:
        cmd = firecrawl_cmd + [
            "search", query,
            "--limit", str(num_results),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            shell=(sys.platform == "win32"),
        )

        if result.returncode == 0 and result.stdout:
            current_title = None
            current_url = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("[PDF]") or (
                    line
                    and not line.startswith("URL:")
                    and not line.startswith("---")
                    and not line.startswith("Content")
                ):
                    if line.startswith("[PDF]"):
                        current_title = line.replace("[PDF]", "").strip().rstrip(" -")
                if line.startswith("URL:"):
                    current_url = line.replace("URL:", "").strip()
                    if current_url and ".pdf" in current_url.lower().split("?")[0]:
                        title = current_title or unquote(
                            urlparse(current_url).path.split("/")[-1]
                        ).replace(".pdf", "")
                        domain = urlparse(current_url).netloc.replace("www.", "")
                        pdfs.append({
                            "url": current_url,
                            "title": title[:150],
                            "source": domain,
                        })
                    current_title = None
                    current_url = None

    except Exception as e:
        print(f"    Search error: {e}")

    return pdfs


def is_junk(title: str) -> bool:
    """Filter out junk PDFs (prospectuses, procurement, disclaimers, etc.)."""
    return bool(JUNK_RE.search(title))


def download_pdf(url, dest_path, timeout=30):
    """Download a PDF file."""
    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=timeout,
            stream=True, allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type and "octet" not in content_type:
            return False, f"Not a PDF ({content_type[:50]})"

        size = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)

        if size < 5000:
            os.unlink(dest_path)
            return False, f"Too small ({size} bytes)"

        return True, f"{size:,} bytes"

    except Exception as e:
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        return False, str(e)


def upload_to_drive(file_path, filename, folder_id):
    """Upload a file to Google Drive using GWS CLI."""
    try:
        cmd = [
            "npx", "@googleworkspace/cli", "drive", "files", "create",
            "--json", json.dumps({
                "name": filename,
                "parents": [folder_id],
            }),
            "--upload", str(file_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            shell=(sys.platform == "win32"),
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                fid = data.get("id", "?")
                return True, fid
            except Exception:
                return True, "ok"
        else:
            return False, result.stderr[:200]
    except Exception as e:
        return False, str(e)


def clean_filename(source, title):
    """Build a clean PDF filename: YYYYMMDD_Issuer_Title.pdf"""
    issuer = DOMAIN_MAP.get(source, source.split(".")[0].title())
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80].strip("_. ")
    safe_title = re.sub(r'_+', '_', safe_title)
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{date_str}_{issuer}_{safe_title}.pdf"


def main():
    parser = argparse.ArgumentParser(description="Daily research PDF fetcher")
    parser.add_argument("--test", action="store_true", help="Discover only, no download")
    parser.add_argument("--limit", type=int, default=0, help="Max PDFs to download (0=all)")
    parser.add_argument("--skip-upload", action="store_true", help="Skip Drive upload")
    parser.add_argument("--reset", action="store_true", help="Reset seen URLs history")
    args = parser.parse_args()

    # Build queries with current month/year for natural recency
    queries = build_queries()

    # Load dedup history
    if args.reset:
        seen_urls = set()
    else:
        seen_urls = load_seen_urls()

    now = datetime.now()
    print(f"{'='*60}")
    print(f"  Daily Research PDF Fetcher")
    print(f"  Period: {now.strftime('%B %Y')}")
    print(f"  Mode: {'TEST' if args.test else 'DOWNLOAD + UPLOAD'}")
    print(f"  Previously seen: {len(seen_urls)} URLs")
    print(f"  Queries: {len(queries)}")
    print(f"{'='*60}\n")

    # Check for Firecrawl
    firecrawl = _firecrawl_cmd()
    if not firecrawl:
        print("  ERROR: Firecrawl CLI not found. Install: npm i -g firecrawl")
        sys.exit(1)
    print(f"  Using Firecrawl for search\n")

    all_pdfs = []
    for i, query in enumerate(queries, 1):
        # Extract readable label
        label = query.replace("filetype:pdf ", "")
        label = re.sub(r'\w+ \d{4}\s*', '', label).split(" site:")[0][:50].strip()
        print(f"[{i}/{len(queries)}] {label}...")
        pdfs = search_pdfs_firecrawl(query, firecrawl, num_results=10)

        # Filter: skip already seen + junk titles
        new_pdfs = []
        for p in pdfs:
            if p["url"] in seen_urls:
                continue
            if is_junk(p["title"]):
                print(f"    SKIP (junk): {p['title'][:60]}")
                continue
            new_pdfs.append(p)

        if new_pdfs:
            for p in new_pdfs:
                print(f"    NEW: [{p['source'][:20]}] {p['title'][:60]}")
            all_pdfs.extend(new_pdfs)
        else:
            print(f"    No new PDFs")
        print()

        time.sleep(1)  # Rate limit

    # Deduplicate by URL
    seen_this_run = set()
    unique_pdfs = []
    for p in all_pdfs:
        if p["url"] not in seen_this_run:
            seen_this_run.add(p["url"])
            unique_pdfs.append(p)

    print(f"\n{'='*60}")
    print(f"  Found {len(unique_pdfs)} new unique PDFs")
    print(f"{'='*60}\n")

    if not unique_pdfs:
        print("  Nothing new today.")
        return

    if args.test:
        results_file = Path(__file__).parent / "_pdf_links.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(unique_pdfs, f, indent=2, ensure_ascii=False)
        print(f"  Results saved to {results_file}")
        for p in unique_pdfs:
            print(f"    [{p['source'][:20]}] {p['title'][:70]}")
        return

    # Download + upload
    to_download = unique_pdfs[:args.limit] if args.limit else unique_pdfs
    tmp_dir = Path(tempfile.mkdtemp(prefix="ix_pdfs_"))
    downloaded = 0
    uploaded = 0
    results = []

    for i, pdf in enumerate(to_download, 1):
        filename = clean_filename(pdf["source"], pdf["title"])
        dest = tmp_dir / filename

        print(f"  [{i}/{len(to_download)}] {filename[:70]}...")
        ok, msg = download_pdf(pdf["url"], dest)
        if ok:
            downloaded += 1
            print(f"    Downloaded: {msg}")

            if not args.skip_upload:
                ok2, msg2 = upload_to_drive(dest, filename, DRIVE_FOLDER_ID)
                if ok2:
                    uploaded += 1
                    print(f"    Uploaded to Drive ({msg2})")
                    results.append({"file": filename, "url": pdf["url"], "status": "uploaded"})
                else:
                    print(f"    Upload failed: {msg2}")
                    results.append({"file": filename, "url": pdf["url"], "status": "upload_failed"})
            else:
                results.append({"file": filename, "url": pdf["url"], "status": "downloaded"})

            # Mark as seen
            seen_urls.add(pdf["url"])
        else:
            print(f"    Failed: {msg}")
            results.append({"file": filename, "url": pdf["url"], "status": f"failed: {msg}"})

    # Save progress
    save_seen_urls(seen_urls)

    # Save results CSV
    results_file = Path(__file__).parent / "_daily_pdf_results.csv"
    with open(results_file, "w", encoding="utf-8") as f:
        f.write("file,url,status\n")
        for r in results:
            f.write(f"{r['file']},{r['url']},{r['status']}\n")

    print(f"\n{'='*60}")
    print(f"  Downloaded: {downloaded}/{len(to_download)}")
    if not args.skip_upload:
        print(f"  Uploaded to Drive: {uploaded}/{downloaded}")
    print(f"  Seen URLs total: {len(seen_urls)}")
    print(f"  Files in: {tmp_dir}")
    print(f"  Results: {results_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
