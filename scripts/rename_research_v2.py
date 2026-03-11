"""
Improved Research PDF Renamer v2.
Renames PDFs in Google Drive based on content (text or image OCR via Gemini).
Format: YYYYMMDD_Issuer_Title_#tags.pdf
"""

import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pdfplumber
import fitz  # PyMuPDF
from google import genai
from google.genai import types

# ── Config ──────────────────────────────────────────────────────────────────
FOLDER_ID = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"
PROGRESS_FILE = Path("D:/investment-x/scripts/_rename_progress_v2.json")
RESULTS_CSV = Path("D:/investment-x/scripts/_rename_results_v2.csv")

# Extract Gemini Key from .env
def get_gemini_key():
    env_path = Path("D:/investment-x/.env")
    if env_path.exists():
        content = env_path.read_text()
        m = re.search(r'GEMINI_API_KEY=([A-Za-z0-9_-]+)', content)
        if m:
            return m.group(1)
    return os.getenv("GEMINI_API_KEY")

GEMINI_KEY = get_gemini_key()
GENAI_CLIENT = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

MONTHS = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
}

ISSUERS = [
    # (pattern, en_name, kr_name)
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
    ("socgen", "SocGen", "SocGen"),
    ("societe generale", "SocGen", "SocGen"),
    ("bernstein", "Bernstein", "Bernstein"),
    ("stifel", "Stifel", "Stifel"),
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
    ("apollo", "Apollo", "Apollo"),
    ("kkr", "KKR", "KKR"),
    ("carlyle", "Carlyle", "Carlyle"),
    ("oaktree", "Oaktree", "Oaktree"),
    ("robeco", "Robeco", "Robeco"),
    ("wisdomtree", "WisdomTree", "WisdomTree"),
    ("yardeni", "Yardeni", "Yardeni"),
    ("research affiliates", "Research-Affiliates", "Research-Affiliates"),
    ("gmo", "GMO", "GMO"),
    ("nber", "NBER", "NBER"),
    ("mckinsey", "McKinsey", "McKinsey"),
    ("bcg", "BCG", "BCG"),
    ("bain", "Bain", "Bain"),
    ("pwc", "PwC", "PwC"),
    ("deloitte", "Deloitte", "Deloitte"),
    ("ey ", "EY", "EY"),
    ("kpmg", "KPMG", "KPMG"),
    ("삼성증권", "Samsung-Securities", "삼성증권"),
    ("미래에셋", "Mirae-Asset", "미래에셋"),
    ("kb증권", "KB-Securities", "KB증권"),
    ("nh투자증권", "NH-Investment", "NH투자증권"),
    ("신한투자증권", "Shinhan-Securities", "신한투자증권"),
    ("하나증권", "Hana-Securities", "하나증권"),
    ("한국투자증권", "Korea-Investment", "한국투자증권"),
    ("대신증권", "Daishin", "대신증권"),
    ("메리츠증권", "Meritz", "메리츠증권"),
    ("한화투자증권", "Hanwha", "한화투자증권"),
    ("유안타증권", "Yuanta", "유안타증권"),
    ("키움증권", "Kiwoom", "키움증권"),
    ("현대차증권", "Hyundai-Motor", "현대차증권"),
    ("교보증권", "Kyobo", "교보증권"),
    ("하이투자증권", "Hi-Investment", "하이투자증권"),
    ("db금융투자", "DB-Financial", "DB금융투자"),
    ("ibk투자증권", "IBK", "IBK투자증권"),
    ("유진투자증권", "Eugene", "유진투자증권"),
    ("토스증권", "Toss", "토스증권"),
    ("한국은행", "BOK", "한국은행"),
    ("bank of korea", "BOK", "한국은행"),
    ("금융위원회", "FSC", "금융위원회"),
    ("금융감독원", "FSS", "금융감독원"),
    ("kdi", "KDI", "KDI"),
    ("bis ", "BIS", "BIS"),
    ("imf", "IMF", "IMF"),
    ("world bank", "World-Bank", "World-Bank"),
    ("oecd", "OECD", "OECD"),
    ("federal reserve", "Fed", "Fed"),
    ("the fed", "Fed", "Fed"),
    ("ecb", "ECB", "ECB"),
    ("boj", "BOJ", "BOJ"),
    ("moody", "Moodys", "Moodys"),
    ("s&p global", "SP-Global", "SP-Global"),
    ("fitch", "Fitch", "Fitch"),
    ("nice신용평가", "NICE", "NICE신용평가"),
    ("한국신용평가", "KIS", "한국신용평가"),
    ("한국기업평가", "KR", "한국기업평가"),
]

TAG_KEYWORDS = {
    '#macro': ['macro', 'gdp', 'economic outlook', 'business cycle', '거시', '경기'],
    '#rates': ['interest rate', 'yield', 'treasury', 'bond', '금리', '채권', '국채'],
    '#credit': ['credit', 'high yield', 'investment grade', 'spread', '신용', '크레딧'],
    '#equity': ['equity', 'stock', 'earnings', 's&p', 'kospi', '주식', '주가'],
    '#fx': ['currency', 'dollar', 'exchange rate', '환율', '달러'],
    '#commodities': ['commodity', 'oil', 'gold', 'copper', '원자재', '유가'],
    '#korea': ['korea', 'kospi', 'kosdaq', '한국', '국내'],
    '#us': ['u.s.', 'united states', 'america', 'fed ', 'fomc', '미국'],
    '#china': ['china', '중국'],
    '#outlook': ['outlook', 'forecast', 'preview', '전망', '예측'],
    '#strategy': ['strategy', 'allocation', 'tactical', '전략', '배분'],
    '#semiconductor': ['semiconductor', 'chip', 'nvidia', '반도체'],
    '#tech': ['technology', 'ai ', 'software', 'IT', '기술'],
    '#geopolitics': ['geopolit', 'tariff', 'sanction', 'war ', '지정학'],
}

# ── Helpers ─────────────────────────────────────────────────────────────────

def gws_cmd(args: str, timeout: int = 60) -> tuple:
    cmd_path = shutil.which("gws") or "gws"
    result = subprocess.run(
        f'"{cmd_path}" {args}',
        shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout, result.returncode

def is_korean(text: str) -> bool:
    if not text: return False
    korean_chars = sum(1 for c in text[:2000] if '\uAC00' <= c <= '\uD7A3')
    latin_chars = sum(1 for c in text[:2000] if 'a' <= c.lower() <= 'z')
    if (korean_chars + latin_chars) == 0: return False
    return korean_chars / (korean_chars + latin_chars) > 0.2

def extract_text(path: str, max_pages: int = 3) -> tuple:
    texts = []
    meta = {}
    try:
        with pdfplumber.open(path) as pdf:
            meta = pdf.metadata or {}
            for p in pdf.pages[:max_pages]:
                t = p.extract_text()
                if t: texts.append(t)
    except: pass
    return "\n".join(texts), meta

def extract_date(text: str, filename: str, pdf_meta: dict) -> str:
    text_snippet = text[:4000]
    
    # 1. YYYYMMDD in filename
    m = re.search(r'^(\d{8})', filename)
    if m: return m.group(1)

    # 2. PDF metadata
    for key in ['CreationDate', 'ModDate']:
        val = str(pdf_meta.get(key, ''))
        m = re.search(r'D:(\d{4})(\d{2})(\d{2})', val)
        if m: return f"{m.group(1)}{m.group(2)}{m.group(3)}"

    # 3. Standard YYYY.MM.DD or YYYY-MM-DD
    m = re.search(r'(20[2-3]\d)[.\-/](\d{1,2})[.\-/](\d{1,2})', text_snippet)
    if m: return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"

    # 4. Korean: 2026년 3월 11일
    m = re.search(r'(20[2-3]\d)년\s*(\d{1,2})월\s*(\d{1,2})일', text_snippet)
    if m: return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"

    # 5. English: March 11, 2026
    m = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(20[2-3]\d)', text_snippet, re.I)
    if m: return f"{m.group(3)}{MONTHS[m.group(1).lower()[:3]]}{int(m.group(2)):02d}"
    
    # 6. English: 11 March 2026
    m = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20[2-3]\d)', text_snippet, re.I)
    if m: return f"{m.group(3)}{MONTHS[m.group(2).lower()[:3]]}{int(m.group(1)):02d}"

    # 7. Outlook 2026 -> 20260101 (approx)
    m = re.search(r'Outlook\s+(202[4-9])', text_snippet, re.I)
    if m: return f"{m.group(1)}0101"

    # 8. Q1 2026
    m = re.search(r'([1-4])Q\s+(20[2-3]\d)', text_snippet, re.I)
    if m: return f"{m.group(2)}{(int(m.group(1))-1)*3+1:02d}01"
    
    m = re.search(r'(20[2-3]\d)\s+([1-4])Q', text_snippet, re.I)
    if m: return f"{m.group(1)}{(int(m.group(2))-1)*3+1:02d}01"

    return "unknown"

def extract_issuer(text: str, filename: str, is_kr: bool) -> str:
    combined = (filename + " " + text[:3000]).lower()
    for pattern, en, kr in ISSUERS:
        if pattern.lower() in combined:
            return kr if is_kr else en
    return "Unknown"

def extract_title(text: str, filename: str, issuer: str) -> str:
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5][:30]
    issuer_clean = issuer.lower().replace('-', ' ')
    candidates = []
    for l in lines:
        lc = l.lower()
        if any(x in lc for x in ['disclaimer', 'copyright', 'all rights', 'http', 'www.', 'confidential']): continue
        if issuer_clean in lc: continue
        if len(l) > 100: continue
        candidates.append(l)
    
    if candidates: title = candidates[0]
    else: title = filename.replace('.pdf', '')
    
    title = re.sub(r'[<>:"\'/\\|?*]', '', title).strip()
    title = re.sub(r'\s+', '-', title)[:60]
    return title

def auto_tag(text: str) -> list:
    text_lower = text[:5000].lower()
    tags = []
    for tag, kws in TAG_KEYWORDS.items():
        if any(kw in text_lower for kw in kws): tags.append(tag)
    return tags[:4]

# ── Gemini Fallback ──────────────────────────────────────────────────────────

def analyze_with_gemini(pdf_path: str, text_content: str, filename: str) -> dict:
    if not GENAI_CLIENT: return None
    
    prompt = f"""
    Analyze this financial research report and provide:
    1. Publication Date (YYYYMMDD format). If only year is found, use YYYY0101.
    2. Issuer/Organization Name (e.g., Goldman Sachs).
    3. Concise Title (max 5-7 words).
    4. 3-4 relevant Hashtags (e.g., #macro, #equity).

    Return ONLY a JSON object: {{"date": "YYYYMMDD", "issuer": "Name", "title": "Title", "tags": ["#tag1", "#tag2"]}}

    Filename: {filename}
    Text content snippet: {text_content[:2000]}
    """
    
    contents = [prompt]
    
    # If text is too short, send the first page as an image
    if len(text_content.strip()) < 300:
        try:
            doc = fitz.open(pdf_path)
            if doc.page_count > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom for better OCR
                img_data = pix.tobytes("png")
                contents.append(types.Part.from_bytes(data=img_data, mime_type="image/png"))
            doc.close()
        except Exception as e:
            print(f"      [Gemini Image Error] {e}")

    try:
        response = GENAI_CLIENT.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"      [Gemini API Error] {e}")
        return None

# ── Main Logic ───────────────────────────────────────────────────────────────

def process_one(f: dict, tmp_dir: str) -> dict:
    fid = f["id"]
    old_name = f["name"]
    
    # Download
    dest = os.path.join(tmp_dir, f"{fid}.pdf")
    _, rc = gws_cmd(f'drive files get --params "{{\\"fileId\\": \\"{fid}\\", \\"alt\\": \\"media\\"}}" -o "{dest}"')
    
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        return {"id": fid, "old": old_name, "status": "fail_download"}
    
    text, meta = extract_text(dest)
    kr = is_korean(text)
    
    date = extract_date(text, old_name, meta)
    issuer = extract_issuer(text, old_name, kr)
    title = extract_title(text, old_name, issuer)
    tags = auto_tag(text)
    
    # Fallback to Gemini if metadata is missing or text is weak
    if date == "unknown" or issuer == "Unknown" or len(text) < 500:
        print(f"      (Using Gemini fallback...)")
        g_data = analyze_with_gemini(dest, text, old_name)
        if g_data and isinstance(g_data, dict):
            date = str(g_data.get("date", date))
            issuer = str(g_data.get("issuer", issuer))
            g_title = g_data.get("title")
            if g_title:
                title = str(g_title).replace(' ', '-')
            g_tags = g_data.get("tags")
            if g_tags and isinstance(g_tags, list):
                tags = g_tags

    # Final cleanup
    try: os.unlink(dest)
    except: pass
    
    new_name = f"{date}_{issuer}_{title}_{' '.join(tags)}".strip('_') + ".pdf"
    new_name = re.sub(r'[<>:"\'/\\|?*]', '', new_name)[:200]
    
    return {
        "id": fid, "old": old_name, "new": new_name, 
        "date": date, "issuer": issuer, "status": "ready"
    }

def list_files():
    stdout, _ = gws_cmd(f'drive files list --params "{{\\"q\\": \\"\\u0027{FOLDER_ID}\\u0027 in parents and mimeType=\\u0027application/pdf\\u0027\\", \\"pageSize\\": 500}}" --page-all --page-limit 5')
    files = []
    for line in stdout.strip().splitlines():
        try: files.extend(json.loads(line).get("files", []))
        except: pass
    return files

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    print(f"Listing files in folder {FOLDER_ID}...")
    all_files = list_files()
    
    to_process = [f for f in all_files if not re.match(r'^\d{8}_', f["name"])][:args.limit]
    print(f"Found {len(all_files)} files, processing {len(to_process)}...")

    tmp_dir = tempfile.mkdtemp()
    results = []
    try:
        for i, f in enumerate(to_process):
            print(f"[{i+1}/{len(to_process)}] {f['name']}")
            res = process_one(f, tmp_dir)
            results.append(res)
            print(f"   => {res.get('new')}")
    finally:
        shutil.rmtree(tmp_dir)

    # Save results
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8-sig") as cf:
        writer = csv.DictWriter(cf, fieldnames=["id", "old", "new", "date", "issuer", "status"])
        writer.writeheader()
        writer.writerows(results)

    if not args.dry_run:
        print("\nExecuting renames...")
        for r in results:
            if r["status"] == "ready":
                gws_cmd(f'drive files update --params "{{\\"fileId\\": \\"{r["id"]}\\"}}" --json "{{\\"name\\": \\"{r["new"]}\\"}}"')
        print("Done!")

if __name__ == "__main__":
    main()
