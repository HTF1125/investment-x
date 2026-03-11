"""
Rename ALL research PDFs in Google Drive "0. Research" folder.
Format: YYYYMMDD_Issuer_Title_#tag1 #tag2.pdf
Language-aware: Korean PDFs get Korean filenames.

Usage:
  python scripts/rename_research.py                # Full run
  python scripts/rename_research.py --dry-run      # Preview only
  python scripts/rename_research.py --limit 10     # Process N files
  python scripts/rename_research.py --resume       # Resume from saved progress
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

import pdfplumber

# ── Config ──────────────────────────────────────────────────────────────────
FOLDER_ID = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"
PROGRESS_FILE = Path("D:/investment-x/scripts/_rename_progress.json")
RESULTS_CSV = Path("D:/investment-x/scripts/_rename_results.csv")

MONTHS = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
}

# Issuer list: (pattern_to_match, english_name, korean_name)
ISSUERS = [
    # Global banks
    ("morgan stanley", "Morgan-Stanley", "Morgan-Stanley"),
    ("goldman sachs", "Goldman-Sachs", "Goldman-Sachs"),
    ("j.p. morgan", "JPMorgan", "JPMorgan"),
    ("jpmorgan", "JPMorgan", "JPMorgan"),
    ("ubs ", "UBS", "UBS"),
    ("credit suisse", "Credit-Suisse", "Credit-Suisse"),
    ("barclays", "Barclays", "Barclays"),
    ("deutsche bank", "Deutsche-Bank", "Deutsche-Bank"),
    ("hsbc", "HSBC", "HSBC"),
    ("bnp paribas", "BNP-Paribas", "BNP-Paribas"),
    ("citigroup", "Citi", "Citi"),
    ("citi ", "Citi", "Citi"),
    ("bank of america", "BofA", "BofA"),
    ("bofa", "BofA", "BofA"),
    ("wells fargo", "Wells-Fargo", "Wells-Fargo"),
    ("nomura", "Nomura", "Nomura"),
    ("mizuho", "Mizuho", "Mizuho"),
    ("daiwa", "Daiwa", "Daiwa"),
    ("macquarie", "Macquarie", "Macquarie"),
    ("rbc ", "RBC", "RBC"),
    ("td securities", "TD-Securities", "TD-Securities"),
    ("raymond james", "Raymond-James", "Raymond-James"),
    ("jefferies", "Jefferies", "Jefferies"),
    ("lazard", "Lazard", "Lazard"),
    ("evercore", "Evercore", "Evercore"),
    ("société générale", "SocGen", "SocGen"),
    ("socgen", "SocGen", "SocGen"),
    ("bernstein", "Bernstein", "Bernstein"),
    ("stifel", "Stifel", "Stifel"),
    # Asset managers
    ("blackrock", "BlackRock", "BlackRock"),
    ("vanguard", "Vanguard", "Vanguard"),
    ("pimco", "PIMCO", "PIMCO"),
    ("fidelity", "Fidelity", "Fidelity"),
    ("state street", "State-Street", "State-Street"),
    ("bridgewater", "Bridgewater", "Bridgewater"),
    ("aqr", "AQR", "AQR"),
    ("man group", "Man-Group", "Man-Group"),
    ("schroders", "Schroders", "Schroders"),
    ("invesco", "Invesco", "Invesco"),
    ("franklin templeton", "Franklin-Templeton", "Franklin-Templeton"),
    ("wellington", "Wellington", "Wellington"),
    ("tcw", "TCW", "TCW"),
    ("pgim", "PGIM", "PGIM"),
    ("nuveen", "Nuveen", "Nuveen"),
    ("apollo", "Apollo", "Apollo"),
    ("kkr", "KKR", "KKR"),
    ("carlyle", "Carlyle", "Carlyle"),
    ("oaktree", "Oaktree", "Oaktree"),
    # Consultancies
    ("mckinsey", "McKinsey", "McKinsey"),
    ("boston consulting", "BCG", "BCG"),
    ("bcg", "BCG", "BCG"),
    ("bain & company", "Bain", "Bain"),
    ("pwc", "PwC", "PwC"),
    ("deloitte", "Deloitte", "Deloitte"),
    ("ernst & young", "EY", "EY"),
    ("kpmg", "KPMG", "KPMG"),
    ("accenture", "Accenture", "Accenture"),
    ("oliver wyman", "Oliver-Wyman", "Oliver-Wyman"),
    # Korean securities
    ("삼성증권", "Samsung-Securities", "삼성증권"),
    ("samsung securities", "Samsung-Securities", "삼성증권"),
    ("미래에셋", "Mirae-Asset", "미래에셋"),
    ("mirae asset", "Mirae-Asset", "미래에셋"),
    ("kb증권", "KB-Securities", "KB증권"),
    ("kb securities", "KB-Securities", "KB증권"),
    ("nh투자증권", "NH-Investment", "NH투자증권"),
    ("nh investment", "NH-Investment", "NH투자증권"),
    ("신한투자증권", "Shinhan-Securities", "신한투자증권"),
    ("shinhan", "Shinhan-Securities", "신한투자증권"),
    ("하나증권", "Hana-Securities", "하나증권"),
    ("hana securities", "Hana-Securities", "하나증권"),
    ("한국투자증권", "Korea-Investment", "한국투자증권"),
    ("korea investment", "Korea-Investment", "한국투자증권"),
    ("대신증권", "Daishin", "대신증권"),
    ("daishin", "Daishin", "대신증권"),
    ("메리츠증권", "Meritz", "메리츠증권"),
    ("meritz", "Meritz", "메리츠증권"),
    ("한화투자증권", "Hanwha", "한화투자증권"),
    ("hanwha", "Hanwha", "한화투자증권"),
    ("유안타증권", "Yuanta", "유안타증권"),
    ("yuanta", "Yuanta", "유안타증권"),
    ("이베스트투자증권", "eBest", "이베스트투자증권"),
    ("ebest", "eBest", "이베스트투자증권"),
    ("sk증권", "SK-Securities", "SK증권"),
    ("키움증권", "Kiwoom", "키움증권"),
    ("kiwoom", "Kiwoom", "키움증권"),
    ("현대차증권", "Hyundai-Motor-Securities", "현대차증권"),
    ("교보증권", "Kyobo", "교보증권"),
    ("하이투자증권", "Hi-Investment", "하이투자증권"),
    ("db금융투자", "DB-Financial", "DB금융투자"),
    ("ibk투자증권", "IBK", "IBK투자증권"),
    ("부국증권", "Bookook", "부국증권"),
    ("케이프투자증권", "Cape", "케이프투자증권"),
    ("한양증권", "Hanyang", "한양증권"),
    ("유진투자증권", "Eugene", "유진투자증권"),
    ("eugene", "Eugene", "유진투자증권"),
    ("토스증권", "Toss", "토스증권"),
    # Korean institutions
    ("한국은행", "BOK", "한국은행"),
    ("bank of korea", "BOK", "한국은행"),
    ("금융위원회", "FSC", "금융위원회"),
    ("금융감독원", "FSS", "금융감독원"),
    ("한국개발연구원", "KDI", "KDI"),
    ("kdi", "KDI", "KDI"),
    ("산업연구원", "KIET", "산업연구원"),
    ("대외경제정책연구원", "KIEP", "KIEP"),
    ("자본시장연구원", "KCMI", "자본시장연구원"),
    ("한국금융연구원", "KIF", "한국금융연구원"),
    # International institutions
    ("bis ", "BIS", "BIS"),
    ("bank for international", "BIS", "BIS"),
    ("imf", "IMF", "IMF"),
    ("international monetary fund", "IMF", "IMF"),
    ("world bank", "World-Bank", "World-Bank"),
    ("oecd", "OECD", "OECD"),
    ("federal reserve", "Fed", "Fed"),
    ("the fed", "Fed", "Fed"),
    ("ecb", "ECB", "ECB"),
    ("european central bank", "ECB", "ECB"),
    ("boj", "BOJ", "BOJ"),
    ("bank of japan", "BOJ", "BOJ"),
    # Ratings / data
    ("moody", "Moodys", "Moodys"),
    ("s&p global", "SP-Global", "SP-Global"),
    ("fitch", "Fitch", "Fitch"),
    ("nice신용평가", "NICE", "NICE신용평가"),
    ("한국신용평가", "KIS", "한국신용평가"),
    ("한국기업평가", "KR", "한국기업평가"),
    # Other
    ("efg", "EFG", "EFG"),
    ("corecommodity", "CoreCommodity", "CoreCommodity"),
    ("balbec", "Balbec", "Balbec"),
    ("흥국생명", "Heungkuk-Life", "흥국생명"),
]

TAG_KEYWORDS = {
    '#macro': ['macro', 'gdp', 'economic outlook', 'business cycle', '거시', '경기'],
    '#rates': ['interest rate', 'yield', 'treasury', 'bond', '금리', '채권', '국채'],
    '#credit': ['credit', 'high yield', 'investment grade', 'spread', '신용', '크레딧'],
    '#equity': ['equity', 'stock', 'earnings', 's&p', 'kospi', '주식', '주가', '시장전망'],
    '#fx': ['currency', 'dollar', 'exchange rate', 'forex', '환율', '달러', '원화'],
    '#commodities': ['commodity', 'oil', 'gold', 'copper', 'mining', '원자재', '유가'],
    '#korea': ['korea', 'kospi', 'kosdaq', '한국', '국내', '코스피', '코스닥'],
    '#us': ['u.s.', 'united states', 'america', 'fed ', 'fomc', '미국'],
    '#china': ['china', 'chinese', '중국', 'pbc', 'pboc'],
    '#japan': ['japan', 'boj', '일본', 'nikkei'],
    '#europe': ['europe', 'ecb', 'eurozone', 'eu ', '유럽'],
    '#em': ['emerging market', 'em ', 'frontier', '신흥국', '이머징'],
    '#global': ['global', 'world', '글로벌', '세계'],
    '#outlook': ['outlook', 'forecast', 'preview', '전망', '예측'],
    '#strategy': ['strategy', 'allocation', 'tactical', '전략', '배분'],
    '#semiconductor': ['semiconductor', 'chip', 'nvidia', 'tsmc', '반도체'],
    '#energy': ['energy', 'oil', 'natural gas', 'renewable', '에너지'],
    '#tech': ['technology', 'ai ', 'artificial intelligence', 'software', 'IT', '기술'],
    '#geopolitics': ['geopolit', 'tariff', 'sanction', 'war ', 'conflict', '관세', '지정학'],
    '#inflation': ['inflation', 'cpi', 'pce', '물가', '인플레이션'],
    '#mining': ['mining', 'mine ', 'mineral', 'extraction', '광업'],
    '#realestate': ['real estate', 'property', 'housing', 'reit', '부동산'],
    '#quant': ['quant', 'factor', 'systematic', '퀀트', '팩터'],
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def gws_cmd(args: str, timeout: int = 30) -> tuple:
    cmd_path = shutil.which("gws") or "gws"
    result = subprocess.run(
        f'"{cmd_path}" {args}',
        shell=True, capture_output=True, text=True, timeout=timeout
    )
    out = result.stdout + result.stderr
    lines = [l for l in out.splitlines() if not l.startswith("Using keyring")]
    return "\n".join(lines), result.returncode


def is_korean(text: str) -> bool:
    """Detect if text is predominantly Korean."""
    if not text:
        return False
    korean_chars = sum(1 for c in text[:2000] if '\uAC00' <= c <= '\uD7A3' or '\u3130' <= c <= '\u318F')
    latin_chars = sum(1 for c in text[:2000] if 'a' <= c.lower() <= 'z')
    total = korean_chars + latin_chars
    if total == 0:
        return False
    return korean_chars / total > 0.3


def extract_text(path: str, max_pages: int = 2) -> tuple:
    """Extract text and PDF metadata."""
    texts = []
    meta = {}
    try:
        with pdfplumber.open(path) as pdf:
            meta = pdf.metadata or {}
            for p in pdf.pages[:max_pages]:
                t = p.extract_text()
                if t:
                    texts.append(t)
    except Exception as e:
        return "", {}
    return "\n".join(texts), meta


def extract_date(text: str, filename: str, pdf_meta: dict) -> str:
    """Extract published date."""
    # 1. Filename as Unix timestamp (Telegram saves)
    base = filename.replace('.pdf', '').strip()
    if base.isdigit() and len(base) >= 13:
        try:
            dt = datetime.fromtimestamp(int(base) / 1000)
            if 2020 <= dt.year <= 2030:
                return dt.strftime("%Y%m%d")
        except:
            pass

    # 2. Filename already starts with YYYYMMDD
    m = re.match(r'^(\d{8})', filename)
    if m:
        return m.group(1)

    # 3. PDF metadata (CreationDate / ModDate)
    for key in ['CreationDate', 'ModDate']:
        val = str(pdf_meta.get(key, ''))
        if val:
            m = re.search(r'D:(\d{4})(\d{2})(\d{2})', val)
            if m:
                return f"{m.group(1)}{m.group(2)}{m.group(3)}"
            m = re.search(r'(\d{4})(\d{2})(\d{2})', val)
            if m and 2020 <= int(m.group(1)) <= 2030:
                return f"{m.group(1)}{m.group(2)}{m.group(3)}"

    # 4. Korean date pattern
    m = re.search(r'(20[2-3]\d)년\s*(\d{1,2})월\s*(\d{1,2})일', text[:3000])
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"

    # 5. Korean compact date: 2026.03.09 or 26.03.09
    m = re.search(r'(20[2-3]\d)[.\-/](\d{1,2})[.\-/](\d{1,2})', text[:3000])
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"

    # 6. English month patterns
    m = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
        text[:3000], re.I
    )
    if m:
        return f"{m.group(3)}{MONTHS[m.group(1).lower()]}{int(m.group(2)):02d}"

    m = re.search(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        text[:3000], re.I
    )
    if m:
        return f"{m.group(3)}{MONTHS[m.group(2).lower()]}{int(m.group(1)):02d}"

    # 7. Month YYYY (no day)
    m = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        text[:3000], re.I
    )
    if m:
        return f"{m.group(2)}{MONTHS[m.group(1).lower()]}00"

    return "unknown"


def extract_issuer(text: str, filename: str, is_kr: bool) -> str:
    """Find issuer/publisher. Returns name in appropriate language."""
    combined = (filename + " " + text[:2000]).lower()
    for pattern, en_name, kr_name in ISSUERS:
        if pattern.lower() in combined:
            return kr_name if is_kr else en_name
    return "Unknown"


def extract_title(text: str, filename: str, issuer_en: str, is_kr: bool) -> str:
    """Extract the report title from text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    skip_words = [
        'disclaimer', 'confidential', 'copyright', 'all rights', 'page ',
        'www.', 'http', 'tel:', 'fax:', 'email:', '@', '본 자료',
        '투자등급', '목표주가', '종목명', 'compliance',
    ]

    # Find the best title candidate from first 25 lines
    candidates = []
    for line in lines[:25]:
        line = line.strip()
        if len(line) < 4 or len(line) > 100:
            continue
        line_lower = line.lower()
        # Skip boilerplate
        if any(s in line_lower for s in skip_words):
            continue
        # Skip if it's just the issuer name
        if issuer_en and line_lower.replace('-', ' ') == issuer_en.lower().replace('-', ' '):
            continue
        # Skip lines that are mostly numbers/symbols
        alpha = sum(1 for c in line if c.isalpha() or '\uAC00' <= c <= '\uD7A3')
        if alpha < len(line) * 0.3:
            continue
        candidates.append(line)

    if candidates:
        title = candidates[0][:60]
    else:
        title = filename.replace('.pdf', '')[:50]

    # Sanitize for filename
    title = re.sub(r'[<>:"\'/\\|?*\[\]]', '', title)
    title = re.sub(r'\s+', '-', title.strip())
    title = title.strip('-')
    return title


def auto_tag(text: str) -> list:
    """Auto-assign tags based on keyword detection."""
    text_lower = text[:5000].lower()
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    return tags[:5]


def sanitize_filename(name: str) -> str:
    """Clean filename for Drive compatibility."""
    name = re.sub(r'[<>:"\'/\\|?*]', '', name)
    name = re.sub(r'\s{2,}', ' ', name)
    name = name.strip('. ')
    # Max 200 chars
    if len(name) > 200:
        base = name[:-4] if name.endswith('.pdf') else name
        name = base[:196] + '.pdf'
    return name


def build_new_name(date: str, issuer: str, title: str, tags: list) -> str:
    """Build the final filename."""
    tag_str = " ".join(tags)
    name = f"{date}_{issuer}_{title}"
    if tag_str:
        name += f"_{tag_str}"
    name += ".pdf"
    return sanitize_filename(name)


def process_one(file_info: dict, tmp_dir: str) -> dict:
    """Process a single file and return rename info."""
    fid = file_info["id"]
    name = file_info["name"]
    size = int(file_info.get("size", 0))

    # Skip if already matches our pattern (YYYYMMDD_Something_...)
    if re.match(r'^\d{8}_[A-Za-z\u3130-\uD7A3]', name):
        return {"id": fid, "old": name, "new": name, "status": "already_named"}

    # Download
    dest = os.path.join(tmp_dir, f"{fid}.pdf")
    escaped_fid = fid.replace('"', '\\"')
    stdout, rc = gws_cmd(
        f'drive files get --params "{{\\"fileId\\": \\"{escaped_fid}\\", \\"alt\\": \\"media\\"}}" --output "{dest}"',
        timeout=60
    )
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        return {"id": fid, "old": name, "new": None, "status": "download_failed"}

    # Extract text
    text, pdf_meta = extract_text(dest, max_pages=2)
    # Clean up immediately
    try:
        os.unlink(dest)
    except OSError:
        pass

    if not text:
        return {"id": fid, "old": name, "new": None, "status": "no_text"}

    # Detect language
    kr = is_korean(text)

    # Extract metadata
    date = extract_date(text, name, pdf_meta)
    issuer = extract_issuer(text, name, kr)
    # Get English issuer name for title extraction skip logic
    issuer_en = extract_issuer(text, name, False)
    title = extract_title(text, name, issuer_en, kr)
    tags = auto_tag(text)

    new_name = build_new_name(date, issuer, title, tags)

    return {
        "id": fid,
        "old": name,
        "new": new_name,
        "lang": "kr" if kr else "en",
        "date": date,
        "issuer": issuer,
        "title": title,
        "tags": tags,
        "status": "ready",
    }


def rename_file(file_id: str, new_name: str) -> bool:
    """Rename a file on Google Drive."""
    escaped_name = new_name.replace('"', '\\"').replace("'", "\\'")
    escaped_id = file_id.replace('"', '\\"')
    stdout, rc = gws_cmd(
        f'drive files update --params "{{\\"fileId\\": \\"{escaped_id}\\"}}" '
        f'--json "{{\\"name\\": \\"{escaped_name}\\"}}"',
        timeout=30
    )
    return rc == 0


def list_all_files() -> list:
    """List ALL PDF files in the Research folder."""
    stdout, rc = gws_cmd(
        f'drive files list '
        f'--params "{{\\"q\\": \\"\\u0027{FOLDER_ID}\\u0027 in parents and mimeType=\\u0027application/pdf\\u0027\\", '
        f'\\"pageSize\\": 1000, '
        f'\\"fields\\": \\"files(id,name,mimeType,modifiedTime,size)\\", '
        f'\\"orderBy\\": \\"modifiedTime desc\\"}}" '
        f'--page-all --page-limit 100',
        timeout=300
    )
    files = []
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            files.extend(data.get("files", []))
        except json.JSONDecodeError:
            pass
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no renames")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process")
    parser.add_argument("--resume", action="store_true", help="Resume from saved progress")
    args = parser.parse_args()

    print("=" * 70)
    print("  Research PDF Renamer — Full Run")
    print("=" * 70)

    # Load previous progress if resuming
    done_ids = set()
    if args.resume and PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
        done_ids = set(progress.get("done_ids", []))
        print(f"  Resuming: {len(done_ids)} files already processed")

    # List all files
    print("\n  Listing files...", flush=True)
    all_files = list_all_files()
    print(f"  Found {len(all_files)} PDFs total")

    # Filter
    to_process = []
    already_named = 0
    skipped_done = 0
    for f in all_files:
        if f["id"] in done_ids:
            skipped_done += 1
            continue
        if re.match(r'^\d{8}_[A-Za-z\u3130-\uD7A3]', f["name"]):
            already_named += 1
            continue
        to_process.append(f)

    print(f"  Already named (skipped): {already_named}")
    if skipped_done:
        print(f"  Previously processed (skipped): {skipped_done}")
    print(f"  To process: {len(to_process)}")

    if args.limit > 0:
        to_process = to_process[:args.limit]
        print(f"  Limited to: {len(to_process)}")

    if not to_process:
        print("\n  Nothing to process!")
        return

    # Process
    results = []
    tmp_dir = tempfile.mkdtemp()
    total = len(to_process)

    try:
        for i, f in enumerate(to_process):
            pct = (i + 1) / total * 100
            size_mb = int(f.get("size", 0)) / 1024 / 1024
            print(f"\n  [{i+1}/{total} {pct:.0f}%] {f['name'][:50]}... ({size_mb:.1f}MB)", flush=True)

            result = process_one(f, tmp_dir)
            results.append(result)

            if result["status"] == "ready":
                print(f"    → {result['new'][:70]}")
            else:
                print(f"    → [{result['status']}]")

            # Save progress incrementally
            done_ids.add(f["id"])
            PROGRESS_FILE.write_text(json.dumps({"done_ids": list(done_ids)}))

    except KeyboardInterrupt:
        print("\n\n  Interrupted! Progress saved.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    ready = [r for r in results if r["status"] == "ready"]
    failed = [r for r in results if r["status"] in ("download_failed", "no_text")]
    skipped = [r for r in results if r["status"] == "already_named"]

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: {len(ready)} ready | {len(failed)} failed | {len(skipped)} skipped")
    print(f"{'=' * 70}")

    # Save results CSV
    if ready:
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8-sig") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=["id", "old", "new", "lang", "status"])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "id": r["id"],
                    "old": r["old"],
                    "new": r.get("new", ""),
                    "lang": r.get("lang", ""),
                    "status": r["status"],
                })
        print(f"\n  Results saved to: {RESULTS_CSV}")

    # Execute renames
    if ready and not args.dry_run:
        print(f"\n  Renaming {len(ready)} files on Google Drive...")
        success = 0
        fail = 0
        for r in ready:
            ok = rename_file(r["id"], r["new"])
            if ok:
                success += 1
            else:
                fail += 1
                print(f"    ✗ Failed: {r['old'][:50]}")

        print(f"\n  Renamed: {success} | Failed: {fail}")
    elif args.dry_run:
        print(f"\n  [DRY RUN] No files renamed. Remove --dry-run to execute.")

    print("\nDone!")


if __name__ == "__main__":
    main()
