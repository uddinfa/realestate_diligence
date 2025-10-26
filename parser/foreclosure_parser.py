import os
import re
import csv
from pathlib import Path
import fitz  # PyMuPDF for PDF reading

print("Starting foreclosure parser")


# ---------- HELPERS ----------
def clean_text(text: str) -> str:
    """Normalize spacing and punctuation."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[“”]', '"', text)
    text = re.sub(r'[’‘]', "'", text)
    text = re.sub(r'[\u2013\u2014]', '-', text)
    return text.strip()


def extract_index(text: str) -> str | None:
    """Extract Index number (e.g., 712220/2022)."""
    m = re.search(r'Index\s*(?:No\.?|Number)[:\s]*([0-9]{3,6}/\d{2,4})', text, re.I)
    return m.group(1) if m else None


def plaintiff_from_filename(filename: str) -> str:
    """
    From a filename like 725949_2022_U_S_BANK_TRUST_NATION_v_
    extract 'US Bank Trust Nation'.
    """
    stem = Path(filename).stem
    m = re.search(r'^\d+_\d+_(.+?)_v_', stem, re.I)
    if not m:
        return "NA"
    raw = m.group(1).replace("_", " ").strip()
    raw = re.sub(r'\bU\s*S\b', 'US', raw, flags=re.I)
    raw = re.sub(r'\bN\s*A\b', 'N.A.', raw, flags=re.I)
    # Title case, but preserve common acronyms
    words = []
    for w in raw.split():
        if w.upper() in ["US", "N.A.", "LLC", "LLP", "FSB", "PLC", "PC", "PLLC"]:
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def extract_borough(text: str) -> str:
    """
    Detect borough based on courthouse or county name in the Notice text.
    """
    t = text.lower()
    borough_keywords = {
        "queens": "Queens",
        "brooklyn": "Brooklyn",
        "bronx": "Bronx",
        "manhattan": "Manhattan",,
        "staten island": "Staten Island",
    }

    for key, val in borough_keywords.items():
        if re.search(rf'\b{key}\s+county\b', t):
            return val
        if re.search(rf'\bcounty\s+of\s+{key}\b', t):
            return val
        if re.search(rf'\b{key}\s+supreme\s+court', t):
            return val
        if re.search(rf'\b{key}\s+supreme\s+courthouse', t):
            return val
        if re.search(rf'supreme\s+court.*?\b{key}\b', t):
            return val
    for key, val in borough_keywords.items():
        if re.search(rf'{key}\s+courthouse', t):
            return val
    return "NA"


# ---------- DATETIME DETECTION ----------
def find_auction_datetime(text: str):
    """Extract auction date and time."""
    t = re.sub(r'\s+', ' ', text)
    low = t.lower()
    anchors = [
        "will sell at public auction",
        "sell at public auction",
        "public auction",
        "auction to the highest bidder"
    ]

    weekday = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*'
    month_date_re = rf'(?:{weekday})?(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{{1,2}},\s*\d{{4}}'
    numeric_date_re = r'\b\d{1,2}/\d{1,2}/\d{4}\b'
    time_re = r'\b\d{1,2}:\d{2}\s*(?:[AP]\.?M\.?|[ap]\.?m\.?|[ap]m)\b'

    date_patterns = [month_date_re, numeric_date_re]

    for a in anchors:
        idx = low.find(a)
        if idx != -1:
            window = t[max(0, idx - 80): idx + 600]
            for dpat in date_patterns:
                m = re.search(rf'(?:on\s+)?({dpat}).{{0,120}}?(at\s+({time_re}))', window, re.I)
                if m:
                    date = m.group(1).strip()
                    time = re.sub(r'\s*\.?\s*', '', m.group(3)).upper().replace("AMON", "AM").replace("PMON", "PM")
                    return (date, time)
                md = re.search(dpat, window, re.I)
                mt = re.search(time_re, window, re.I)
                if md and mt:
                    return (md.group(0).strip(), mt.group(0).strip().upper())

    return ("NA", "NA")


# ---------- PARSERS ----------
def parse_notice(text: str, filename: str) -> dict:
    """Extract details from Notice of Sale documents."""
    data = {
        "Index Number": "NA",
        "Plaintiff": "NA",
        "Property Address": "NA",
        "Borough": "NA",
        "Block": "NA",
        "Lot": "NA",
        "Auction Date": "NA",
        "Auction Time": "NA",
        "Referee": "NA",
        "Judgment Amount": "NA",
        "Auction Status": "NA"
    }

    t = clean_text(text)
    m = re.search(r'Index\s*(?:No\.?|Number)[:\s]*([0-9]{3,6}/\d{2,4})', t, re.I)
    if m:
        data["Index Number"] = m.group(1).strip()

    data["Plaintiff"] = plaintiff_from_filename(filename)
    data["Borough"] = extract_borough(text)

    # Property Address (capture full address)
    m = re.search(
        r'(?:premises|property)\s+(?:known\s+as|located\s+at|being)\s*(.*?)(?=(?:block\s|lot\s|county\s|all that certain|tax map|section\s|district\s|premises\s|$))',
        t, re.I
    )
    if m:
        address = m.group(1).strip()
        address = re.sub(r'\b(Block|Lot|County|Section|District|Tax Map).*$', '', address, flags=re.I)
        data["Property Address"] = address.strip().rstrip(".,;:")

    # Block / Lot (dedupe)
    block_lot_patterns = [
        r'Block\s*[:#]?\s*(\d{3,6})\s*(?:,|and| )+\s*Lot\s*[:#]?\s*(\d{1,4})',
        r'Block\s*[:#]?\s*(\d{3,6})\s*Lot\s*[:#]?\s*(\d{1,4})',
        r'tax\s*map\s*(?:identification|id)[:\s#-]*?(\d{3,6})[-–](\d{1,4})',
        r'(\d{3,6})[-–](\d{1,4})'
    ]
    found_pairs = []
    for pattern in block_lot_patterns:
        for match in re.finditer(pattern, t, re.I):
            found_pairs.append((match.group(1), match.group(2)))

    if found_pairs:
        unique_pairs = list(dict.fromkeys(found_pairs))
        data["Block"], data["Lot"] = unique_pairs[0]
        if len(unique_pairs) > 1:
            print(f"Multiple block/lot matches in {filename}: {unique_pairs}")
    else:
        print(f"No block/lot found in {filename}")

    # Referee
    m = re.search(r'([A-Z][A-Za-z .\'\-]+),\s*Esq.*Referee', t)
    if not m:
        m = re.search(r'Referee[:,]?\s*([A-Z][A-Za-z .\'\-]+)', t)
    if m:
        data["Referee"] = m.group(1).strip()

    # Judgment Amount
    m = re.search(r'Judgment amount\s*\$?([\d,]+\.\d{2})', t, re.I)
    if not m:
        m = re.search(r'Approximate\s*Amount\s*of\s*Judgment\s*(?:is\s+)?\$?([\d,]+\.\d{2})', t, re.I)
    if m:
        data["Judgment Amount"] = m.group(1)

    # Auction Date / Time
    date_str, time_str = find_auction_datetime(t)
    data["Auction Date"] = date_str
    data["Auction Time"] = time_str

    return data


def parse_judgment(text: str) -> dict:
    """Extract supplemental data from Judgment of Foreclosure & Sale documents."""
    data = {"Judgment Amount": "NA"}
    t = clean_text(text)

    judgment_patterns = [
        r'showing the sum of\s*\$?([\d,]+\.\d{2})',
        r'principal balance of\s*\$?([\d,]+\.\d{2})',
        r'Amount due per Referee[’\'s]{0,2} Report[:\s]*\$?([\d,]+\.\d{2})',
        r'judgment of foreclosure and sale in the amount of\s*\$?([\d,]+\.\d{2})',
        r'the sum of\s*\$?([\d,]+\.\d{2})\s*(?:was|is)?\s*due'
    ]

    found_amounts = []
    for pattern in judgment_patterns:
        for m in re.finditer(pattern, t, re.I):
            amt_str = m.group(1).replace(",", "")
            try:
                if float(amt_str) > 50000:
                    found_amounts.append(float(amt_str))
            except:
                continue

    if not found_amounts:
        for m in re.finditer(r'\$?([\d,]+\.\d{2})', t):
            amt_str = m.group(1).replace(",", "")
            try:
                if float(amt_str) > 50000:
                    found_amounts.append(float(amt_str))
            except:
                continue

    if found_amounts:
        data["Judgment Amount"] = f"{max(found_amounts):,.2f}"

    return data


def parse_affirmation_status(text: str) -> str:
    """Extract auction status from affirmation/letters."""
    text = clean_text(text).lower()
    if "postpone" in text or "postponed" in text:
        return "Postponed"
    if "cancelled" in text or "canceled" in text:
        return "Cancelled"
    if "rescheduled" in text or "adjourned" in text:
        return "Rescheduled"
    if "may be postponed" in text or "subject to postponement" in text:
        return "Might be postponed"
    if "as scheduled" in text or "will proceed" in text:
        return "Proceeding as scheduled"
    return "NA"


# ---------- MAIN ----------
def parse_multi_folder(notice_folder, judgment_folder, affirmation_folder, output_csv):
    """Integrate three folders into one clean CSV."""
    cases = {}

    def read_pdfs(folder):
        pdfs = []
        for f in Path(folder).glob("*.pdf"):
            with fitz.open(f) as doc:
                text = " ".join(page.get_text("text") for page in doc)
            pdfs.append((f, clean_text(text)))
        return pdfs

    print("🔹 Reading Notice of Sale PDFs...")
    for f, text in read_pdfs(notice_folder):
        index = extract_index(text)
        if not index:
            continue
        data = parse_notice(text, f.name)
        data["Source Notice"] = f.name
        cases[index] = data

    print("🔹 Reading Judgment PDFs...")
    for f, text in read_pdfs(judgment_folder):
        index = extract_index(text)
        if not index or index not in cases:
            continue
        j_data = parse_judgment(text)
        if cases[index]["Judgment Amount"] == "NA" and j_data["Judgment Amount"] != "NA":
            cases[index]["Judgment Amount"] = j_data["Judgment Amount"]
            cases[index]["Source Judgment"] = f.name

    print("🔹 Reading Affirmation PDFs (status updates)...")
    for f, text in read_pdfs(affirmation_folder):
        index = extract_index(text)
        if not index or index not in cases:
            continue
        status = parse_affirmation_status(text)
        if status != "NA":
            cases[index]["Auction Status"] = status
            cases[index]["Source Affirmation"] = f.name

    # Final CSV schema
    fieldnames = [
        "Index Number", "Plaintiff", "Property Address", "Borough",
        "Block", "Lot", "Auction Date", "Auction Time",
        "Referee", "Judgment Amount", "Auction Status",
        "Source Notice", "Source Judgment", "Source Affirmation"
    ]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in cases.values():
            writer.writerow(d)

    print(f"\n Done! Parsed {len(cases)} cases. Results saved to {output_csv}")


# ---------- RUN ----------
if __name__ == "__main__":
    base = Path(".")
    notice_folder = input("📂 Path to Notice of Sale folder: ").strip() or str(base / "notices")
    judgment_folder = input("📂 Path to Judgment folder: ").strip() or str(base / "judgments")
    affirmation_folder = input("📂 Path to Affirmation folder: ").strip() or str(base / "affirmations")
    output_csv = "combined_output.csv"

    for folder in [notice_folder, judgment_folder, affirmation_folder]:
        Path(folder).mkdir(exist_ok=True)

    parse_multi_folder(notice_folder, judgment_folder, affirmation_folder, output_csv)


if __name__ == "__main__":
    # example: show users how they'd run it (adjust paths as you like)
    print("This is the foreclosure parser entrypoint.)
