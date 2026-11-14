"""
TCB Daily Retail Market Price files (Bangla)  ->  ONE clean English Excel file.

* Uses ONLY Python's built-in libraries (no pip install needed).
* Reads every .xlsx in   Downloads/TCB_Daily_RMP
* Writes                 Downloads/TCB_Combined_English.xlsx   (formatted)
                         Downloads/TCB_Combined_English.csv    (for pandas / models)

Sheets in the output:
  Prices          one row per date + item  (long / tidy format - best for models)
  Wide_Avg_Price  one row per date, one column per item (average price)
  Files_Log       every input file: OK / FAILED, rows found, reason
  Untranslated    Bangla names the script could not translate (add them to
                  my_translations.csv and run again)

Optional: put a file called my_translations.csv next to this script with lines:
  bangla name,English name,Category
"""

import csv
import os
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

# ---------------- settings ----------------
HOME = os.path.expanduser("~")
INPUT_FOLDER = os.path.join(HOME, "Downloads", "TCB_Daily_RMP")
OUTPUT_XLSX = os.path.join(HOME, "Downloads", "TCB_Combined_English.xlsx")
OUTPUT_CSV = os.path.join(HOME, "Downloads", "TCB_Combined_English.csv")
# ------------------------------------------

# =====================================================================
# 1. TRANSLATION TABLES
# =====================================================================
# Bangla product name -> (English name, Category)
PRODUCTS = {
    # Rice
    "চাল সুগন্ধী (পোলাও)": ("Rice - Aromatic (Polao)", "Rice"),
    "চাল সুগন্ধি (পোলাও)": ("Rice - Aromatic (Polao)", "Rice"),
    "চাল সরু (নাজির/মিনিকেট)": ("Rice - Fine (Nazir/Miniket)", "Rice"),
    "চাল (সরু) নাজির/মিনিকেট": ("Rice - Fine (Nazir/Miniket)", "Rice"),
    "চাল (মাঝারী)পাইজাম/আটাশ": ("Rice - Medium (Paijam)", "Rice"),
    "চাল (মাঝারি)পাইজাম/আটাশ": ("Rice - Medium (Paijam)", "Rice"),
    "চাল (মাঝারী)পাইজাম/লতা": ("Rice - Medium (Paijam)", "Rice"),
    "চাল (মোটা)/স্বর্ণা/চায়না ইরি": ("Rice - Coarse (Swarna/China IRRI)", "Rice"),
    "চাল (মোটা) স্বর্ণা/চায়না ইরি": ("Rice - Coarse (Swarna/China IRRI)", "Rice"),
    # Flour
    "আটা সাদা (খোলা)": ("Atta (Wheat Flour) - Loose", "Flour"),
    "আটা (খোলা)": ("Atta (Wheat Flour) - Loose", "Flour"),
    "আটা (প্যাকেট)": ("Atta (Wheat Flour) - Packet", "Flour"),
    "ময়দা (খোলা)": ("Maida (Refined Flour) - Loose", "Flour"),
    "ময়দা (প্যাকেট)": ("Maida (Refined Flour) - Packet", "Flour"),
    # Edible oil
    "সয়াবিন তেল (লুজ)": ("Soybean Oil - Loose", "Edible Oil"),
    "সয়াবিন তেল (খোলা)": ("Soybean Oil - Loose", "Edible Oil"),
    "সয়াবিন তেল (বোতল)": ("Soybean Oil - Bottled", "Edible Oil"),
    "পাম অয়েল (লুজ)": ("Palm Oil - Loose", "Edible Oil"),
    "পাম অয়েল (খোলা)": ("Palm Oil - Loose", "Edible Oil"),
    "পাম অয়েল (বোতল)": ("Palm Oil - Bottled", "Edible Oil"),
    "সুপার পাম অয়েল (লুজ)": ("Super Palm Oil - Loose", "Edible Oil"),
    "পাম অয়েল সুপার (লুজ)": ("Super Palm Oil - Loose", "Edible Oil"),
    "রাইস ব্রান তেল (বোতল)": ("Rice Bran Oil - Bottled", "Edible Oil"),
    "রাইস ব্রান তেল (লুজ)": ("Rice Bran Oil - Loose", "Edible Oil"),
    "সরিষার তেল": ("Mustard Oil", "Edible Oil"),
    "সরিষার তেল (বোতল)": ("Mustard Oil - Bottled", "Edible Oil"),
    # Pulses
    "মশুর ডাল (বড় দানা)": ("Lentil (Masur) - Large Grain", "Pulses"),
    "মশুর ডাল (মাঝারী দানা)": ("Lentil (Masur) - Medium Grain", "Pulses"),
    "মশুর ডাল (ছোট দানা)": ("Lentil (Masur) - Small Grain", "Pulses"),
    "মসুর ডাল (বড় দানা)": ("Lentil (Masur) - Large Grain", "Pulses"),
    "মসুর ডাল (মাঝারী দানা)": ("Lentil (Masur) - Medium Grain", "Pulses"),
    "মসুর ডাল (ছোট দানা)": ("Lentil (Masur) - Small Grain", "Pulses"),
    "মুগ ডাল (মানভেদে)": ("Mung Dal (by quality)", "Pulses"),
    "মুগ ডাল": ("Mung Dal", "Pulses"),
    "এ্যাংকর ডাল": ("Anchor Dal (Split Pea)", "Pulses"),
    "অ্যাংকর ডাল": ("Anchor Dal (Split Pea)", "Pulses"),
    "ছোলা (মানভেদে)": ("Chickpea (by quality)", "Pulses"),
    "ছোলা": ("Chickpea", "Pulses"),
    "খেসারি ডাল": ("Khesari Dal (Grass Pea)", "Pulses"),
    "মটর ডাল": ("Pea Dal", "Pulses"),
    # Potato / Spices
    "আলু (নতুন/পুরাতন)": ("Potato", "Vegetables"),
    "আলু": ("Potato", "Vegetables"),
    "আলু (মানভেদে)": ("Potato", "Vegetables"),
    "আলু (নতুন, মানভেদে)": ("Potato", "Vegetables"),
    "আলু (নতুন/পুরাতন)(মানভেদে)": ("Potato", "Vegetables"),
    # name variants TCB used over the years -> one series each
    "পিঁয়াজ (দেশী)(নতুন/পুরাতন)": ("Onion - Local", "Spices"),
    "পিঁয়াজ (নতুন) (দেশী)": ("Onion - Local", "Spices"),
    "পিঁয়াজ (নতুন/পুরাতন) (দেশী)": ("Onion - Local", "Spices"),
    "পিঁয়াজ (দেশী": ("Onion - Local", "Spices"),
    "রসুন(দেশী) নতুন/পুরাতন)": ("Garlic - Local", "Spices"),
    "রসুন(দেশী) নতুন/পুরাতন": ("Garlic - Local", "Spices"),
    "রসুন (দেশী) নতুন/পুরাতন": ("Garlic - Local", "Spices"),
    "রসুন(দেশী) নতুন": ("Garlic - Local", "Spices"),
    "রসুন(দেশী) পুরাতন": ("Garlic - Local", "Spices"),
    "আদা (দেশী)(নতুন)": ("Ginger - Local", "Spices"),
    "আদা (দেশী) নতুন": ("Ginger - Local", "Spices"),
    "মশূর ডাল (মাঝারী দানা)": ("Lentil (Masur) - Medium Grain", "Pulses"),
    "লবণ(প্যাঃ)আয়োডিনযুক্ত(মানভেদে)": ("Salt - Iodized (Packet)", "Miscellaneous"),
    "পাম অয়েল (সুপার)": ("Super Palm Oil - Loose", "Edible Oil"),
    "পাম অলিন (বোতল)": ("Palm Olein - Bottled", "Edible Oil"),
    "পিঁয়াজ (দেশী)": ("Onion - Local", "Spices"),
    "পিঁয়াজ (আমদানি)": ("Onion - Imported", "Spices"),
    "পেঁয়াজ (দেশী)": ("Onion - Local", "Spices"),
    "পেঁয়াজ (আমদানি)": ("Onion - Imported", "Spices"),
    "রসুন (দেশী)": ("Garlic - Local", "Spices"),
    "রসুন (আমদানি)": ("Garlic - Imported", "Spices"),
    "শুকনা মরিচ (দেশী)": ("Dried Chilli - Local", "Spices"),
    "শুকনা মরিচ (আমদানি)": ("Dried Chilli - Imported", "Spices"),
    "হলুদ (দেশী)": ("Turmeric - Local", "Spices"),
    "হলুদ (আমদানি)": ("Turmeric - Imported", "Spices"),
    "আদা (দেশী)": ("Ginger - Local", "Spices"),
    "আদা (আমদানি)": ("Ginger - Imported", "Spices"),
    "জিরা": ("Cumin", "Spices"),
    "দারুচিনি": ("Cinnamon", "Spices"),
    "লবঙ্গ": ("Clove", "Spices"),
    "এলাচ(ছোট)": ("Cardamom (Small)", "Spices"),
    "এলাচ (ছোট)": ("Cardamom (Small)", "Spices"),
    "ধনে": ("Coriander Seed", "Spices"),
    "তেজপাতা": ("Bay Leaf", "Spices"),
    # Fish & meat
    "রুই": ("Rui Fish (Rohu)", "Fish & Meat"),
    "ইলিশ": ("Hilsa Fish", "Fish & Meat"),
    "পাঙ্গাস": ("Pangas Fish", "Fish & Meat"),
    "তেলাপিয়া": ("Tilapia Fish", "Fish & Meat"),
    "গরু": ("Beef", "Fish & Meat"),
    "গরুর মাংস": ("Beef", "Fish & Meat"),
    "খাসী": ("Mutton (Goat)", "Fish & Meat"),
    "খাসির মাংস": ("Mutton (Goat)", "Fish & Meat"),
    "মুরগী(ব্রয়লার)": ("Chicken - Broiler", "Fish & Meat"),
    "মুরগী (ব্রয়লার)": ("Chicken - Broiler", "Fish & Meat"),
    "মুরগী (দেশী)": ("Chicken - Local (Deshi)", "Fish & Meat"),
    "মুরগী (সোনালী)": ("Chicken - Sonali", "Fish & Meat"),
    "মুরগী(সোনালী)": ("Chicken - Sonali", "Fish & Meat"),
    # Powdered milk (brand names)
    "ডানো": ("Powdered Milk - Dano", "Powdered Milk"),
    "ডিপ্লোমা (নিউজিল্যান্ড)": ("Powdered Milk - Diploma (New Zealand)", "Powdered Milk"),
    "ফ্রেশ": ("Powdered Milk - Fresh", "Powdered Milk"),
    "মার্কস": ("Powdered Milk - Marks", "Powdered Milk"),
    # Miscellaneous
    "চিনি": ("Sugar", "Miscellaneous"),
    "চিনি (প্যাকেট)": ("Sugar - Packet", "Miscellaneous"),
    "খেজুর(সাধারণ মানের)": ("Dates (Ordinary Quality)", "Miscellaneous"),
    "খেজুর (সাধারণ মানের)": ("Dates (Ordinary Quality)", "Miscellaneous"),
    "লবণ(প্যাঃ)আয়োডিনযুক্ত": ("Salt - Iodized (Packet)", "Miscellaneous"),
    "লবণ (প্যাঃ) আয়োডিনযুক্ত": ("Salt - Iodized (Packet)", "Miscellaneous"),
    "লেবু": ("Lemon", "Vegetables"),
    "কাঁচামরিচ": ("Green Chilli", "Vegetables"),
    "কাঁচা মরিচ": ("Green Chilli", "Vegetables"),
    "বেগুন": ("Brinjal (Eggplant)", "Vegetables"),
    "শসা": ("Cucumber", "Vegetables"),
    "টমেটো": ("Tomato", "Vegetables"),
    "ডিম (ফার্ম)": ("Egg - Farm", "Miscellaneous"),
    "ডিম(ফার্ম)": ("Egg - Farm", "Miscellaneous"),
    "লেখার কাগজ(সাদা)": ("Writing Paper (White)", "Miscellaneous"),
    "লেখার কাগজ (সাদা)": ("Writing Paper (White)", "Miscellaneous"),
    "এম,এস রড (৬০ গ্রেড)": ("MS Rod (60 Grade)", "Construction"),
    "এম,এস রড( ৪০ গ্রেড)": ("MS Rod (40 Grade)", "Construction"),
    "এম,এস রড (৪০ গ্রেড)": ("MS Rod (40 Grade)", "Construction"),
}

# Word-by-word fallback (used only when a full name is not in the table above)
WORDS = {
    "চাল": "Rice", "সুগন্ধী": "Aromatic", "সরু": "Fine", "মাঝারী": "Medium",
    "মাঝারি": "Medium", "মোটা": "Coarse", "আটা": "Atta", "ময়দা": "Maida",
    "সাদা": "White", "লাল": "Red", "খোলা": "Loose", "লুজ": "Loose",
    "প্যাকেট": "Packet", "প্যাঃ": "Packet", "বোতল": "Bottled", "তেল": "Oil",
    "সয়াবিন": "Soybean", "পাম": "Palm", "অয়েল": "Oil", "সুপার": "Super",
    "সরিষার": "Mustard", "ডাল": "Dal", "মশুর": "Lentil", "মসুর": "Lentil",
    "মুগ": "Mung", "ছোলা": "Chickpea", "বড়": "Large", "ছোট": "Small",
    "দানা": "Grain", "মানভেদে": "(by quality)", "দেশী": "Local", "দেশি": "Local",
    "আমদানি": "Imported", "আমদানী": "Imported", "নতুন": "New", "পুরাতন": "Old",
    "আলু": "Potato", "পিঁয়াজ": "Onion", "পেঁয়াজ": "Onion", "রসুন": "Garlic",
    "মরিচ": "Chilli", "শুকনা": "Dried", "কাঁচা": "Green", "হলুদ": "Turmeric",
    "আদা": "Ginger", "জিরা": "Cumin", "এলাচ": "Cardamom", "মাছ": "Fish",
    "মুরগী": "Chicken", "মুরগি": "Chicken", "ব্রয়লার": "Broiler",
    "সোনালী": "Sonali", "গরু": "Beef", "খাসী": "Mutton", "ডিম": "Egg",
    "ফার্ম": "Farm", "হাঁস": "Duck", "চিনি": "Sugar", "লবণ": "Salt",
    "দুধ": "Milk", "গুড়া": "Powdered", "গুঁড়া": "Powdered", "টমেটো": "Tomato",
    "বেগুন": "Brinjal", "শসা": "Cucumber", "লেবু": "Lemon", "রড": "Rod",
    "গ্রেড": "Grade", "কাগজ": "Paper", "নিউজিল্যান্ড": "New Zealand",
}

CATEGORY_HEADERS = {
    "আটা/ময়দা": "Flour", "ভোজ্য তেল": "Edible Oil", "ডাল": "Pulses",
    "মসলা": "Spices", "মাছ ও গোশত": "Fish & Meat", "মাছ ও মাংস": "Fish & Meat",
    "গুড়া দুধ(প্যাকেটজাত)": "Powdered Milk", "গুঁড়া দুধ(প্যাকেটজাত)": "Powdered Milk",
    "বিবিধ": "Miscellaneous", "চাল": "Rice", "শাকসবজি": "Vegetables",
}

UNIT_WORDS = [
    ("মেঃটন", "metric ton"), ("মে:টন", "metric ton"), ("মেট্রিক টন", "metric ton"),
    ("কেজি", "kg"), ("লিটার", "litre"), ("গ্রাম", "g"),
    ("হালি", "hali (4 pcs)"), ("ডজন", "dozen"), ("দিস্তা", "dista (24 sheets)"),
    ("পিস", "piece"), ("প্রতি", "per"),
]
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
BN_MONTHS = {
    "জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3,
    "এপ্রিল": 4, "মে": 5, "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "আগষ্ট": 8,
    "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11, "ডিসেম্বর": 12,
}


def norm(s):
    """Normalise Bangla text so small spelling/spacing differences still match."""
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("‌", "").replace("‍", "")
    s = re.sub(r"\s+", "", s)
    return s.rstrip(":ঃ-")


PRODUCT_LOOKUP = {norm(k): v for k, v in PRODUCTS.items()}
WORD_LOOKUP = {norm(k): v for k, v in WORDS.items()}
CATEGORY_LOOKUP = {norm(k): v for k, v in CATEGORY_HEADERS.items()}
MONTH_LOOKUP = {norm(k): v for k, v in BN_MONTHS.items()}


def load_user_translations():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_translations.csv")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                cat = row[2].strip() if len(row) > 2 and row[2].strip() else ""
                PRODUCT_LOOKUP[norm(row[0])] = (row[1].strip(), cat)
    print(f"Loaded extra translations from {path}")


def translate_product(bn):
    """Returns (english, category_or_empty, status) status = exact|auto|missing"""
    key = norm(bn)
    if key in PRODUCT_LOOKUP:
        en, cat = PRODUCT_LOOKUP[key]
        return en, cat, "exact"
    tokens = [t for t in re.split(r"[\s()/,]+", unicodedata.normalize("NFC", bn)) if t.strip()]
    out = []
    for t in tokens:
        t2 = t.translate(BN_DIGITS)
        if re.fullmatch(r"[\d.]+", t2):
            out.append(t2)
        elif norm(t) in WORD_LOOKUP:
            out.append(WORD_LOOKUP[norm(t)])
        else:
            return bn.strip(), "", "missing"
    return " ".join(out), "", "auto"


def translate_unit(bn):
    if bn is None:
        return ""
    if re.fullmatch(r"[\d০-৯.,\s-]+", str(bn).strip()):  # TCB typo: price typed in unit cell
        return "per kg"
    s = unicodedata.normalize("NFC", str(bn)).translate(BN_DIGITS).strip()
    packet = bool(re.search("প্যাঃ|প্যাকেট", s))
    s = re.sub("প্যাঃ|প্যাকেট", "", s)
    for b, e in UNIT_WORDS:
        s = s.replace(unicodedata.normalize("NFC", b), " " + e + " ")
    s = re.sub(r"\s+", " ", s).strip()
    if packet:
        s += " (packet)"
    return s


# =====================================================================
# 2. MINIMAL XLSX READER (built-in libraries only)
# =====================================================================
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def col_to_idx(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """Returns list of sheets; each sheet = list of rows (lists of values)."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                if _local(si.tag) != "si":
                    continue
                parts = []
                for el in si.iter():
                    if _local(el.tag) == "t" and el.text:
                        parts.append(el.text)
                    if _local(el.tag) == "rPh":  # phonetic hints - skip
                        break
                shared.append("".join(parts))

        # find sheet files in workbook order
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.get("Id"): r.get("Target") for r in rels}
        sheet_paths = []
        for el in wb.iter():
            if _local(el.tag) == "sheet":
                rid = next((v for k, v in el.attrib.items() if k.endswith("}id")), None)
                tgt = rel_map.get(rid, "")
                tgt = tgt.lstrip("/")
                if not tgt.startswith("xl/"):
                    tgt = "xl/" + tgt
                if tgt in names:
                    sheet_paths.append(tgt)

        sheets = []
        for sp in sheet_paths:
            rows = {}
            root = ET.fromstring(z.read(sp))
            for row in root.iter():
                if _local(row.tag) != "row":
                    continue
                r_idx = int(row.get("r", len(rows) + 1)) - 1
                cells = {}
                for c in row:
                    if _local(c.tag) != "c":
                        continue
                    ref = c.get("r")
                    ci = col_to_idx(ref) if ref else len(cells)
                    t = c.get("t")
                    v = None
                    has_formula = False
                    for ch in c:
                        ln = _local(ch.tag)
                        if ln == "v":
                            v = ch.text
                        elif ln == "f":
                            has_formula = True
                        elif ln == "is":
                            v = "".join(x.text or "" for x in ch.iter() if _local(x.tag) == "t")
                    if has_formula:
                        continue  # formula columns (% change) are recomputed later
                    if v is None:
                        continue
                    if t == "s":
                        v = shared[int(v)] if int(v) < len(shared) else ""
                    elif t in ("str", "inlineStr", "e", "b"):
                        pass
                    else:
                        try:
                            f = float(v)
                            v = int(f) if f.is_integer() else f
                        except ValueError:
                            pass
                    cells[ci] = v
                rows[r_idx] = cells
            if not rows:
                sheets.append([])
                continue
            max_r = max(rows)
            grid = []
            for r in range(max_r + 1):
                cells = rows.get(r, {})
                width = (max(cells) + 1) if cells else 0
                grid.append([cells.get(i) for i in range(width)])
            sheets.append(grid)
    return sheets


# =====================================================================
# 3. PARSE ONE TCB FILE
# =====================================================================
def txt(v):
    return "" if v is None else unicodedata.normalize("NFC", str(v)).strip()


def cell(row, i):
    return row[i] if i is not None and 0 <= i < len(row) else None


def to_price(v):
    """Number or None. 0 / blank / dash means 'not available' -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v if v > 0 else None
    s = txt(v).translate(BN_DIGITS).replace(",", "")
    m = re.fullmatch(r"\d+(\.\d+)?", s)
    if m:
        f = float(s)
        if f <= 0:
            return None
        return int(f) if f.is_integer() else f
    return None


def excel_serial_to_date(n):
    return date(1899, 12, 30) + timedelta(days=int(n))


def find_date(grid, header_r, today_col):
    # a) date cell under "today price" heading
    if header_r is not None and today_col is not None:
        for r in range(header_r + 1, min(header_r + 3, len(grid))):
            v = cell(grid[r], today_col)
            if isinstance(v, (int, float)) and 30000 < v < 60000:
                return excel_serial_to_date(v), "header date cell"
            if isinstance(v, str):
                d = parse_date_text(v)
                if d:
                    return d, "header date cell"
    # b) "তারিখঃ dd-mm-yyyy" or Bangla written date in the top rows
    for r in range(min(8, len(grid))):
        line = " ".join(txt(x) for x in grid[r] if x is not None)
        m = re.search(r"তারিখ\s*[ঃ:]?\s*([০-৯\d]{1,2})[-./]([০-৯\d]{1,2})[-./]([০-৯\d]{4})", line)
        if m:
            d, mo, y = (int(x.translate(BN_DIGITS)) for x in m.groups())
            try:
                return date(y, mo, d), "তারিখ line"
            except ValueError:
                pass
    for r in range(min(8, len(grid))):
        line = " ".join(txt(x) for x in grid[r] if x is not None)
        d = parse_bangla_written_date(line)
        if d:
            return d, "written date line"
    return None, ""


def parse_date_text(s):
    s = txt(s).translate(BN_DIGITS)
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_bangla_written_date(line):
    # e.g. "সোমবার ৩১ আগষ্ট ২০২৬ খ্রিঃ"
    m = re.search(r"([০-৯\d]{1,2})\s+(\S+)\s+([০-৯\d]{4})\s*খ্রি", line)
    if m:
        mo = MONTH_LOOKUP.get(norm(m.group(2)))
        if mo:
            try:
                return date(int(m.group(3).translate(BN_DIGITS)), mo,
                            int(m.group(1).translate(BN_DIGITS)))
            except ValueError:
                return None
    return None


def parse_tcb_sheet(grid):
    """Return (records, info) or raise ValueError with the reason."""
    # --- locate header row(s)
    header_rows = [r for r, row in enumerate(grid)
                   if any("পণ্যের নাম" in txt(v) for v in row)]
    cols = {}
    layout = "detected"
    if header_rows:
        h = grid[header_rows[0]]
        for i, v in enumerate(h):
            t = txt(v)
            if "পণ্যের নাম" in t:
                cols["name"] = i
            elif "একক" in t:
                cols["unit"] = i
            elif "অদ্যকার" in t or "আজকের" in t:
                cols["today"] = i
            elif "সপ্তাহ" in t:
                cols["week"] = i
            elif "বছর" in t:
                cols["year"] = i
            elif "মাস" in t and "মাসিক" not in t:
                cols["month"] = i
        # refine min/max positions from the "সর্বনিম্ন / সর্বোচ্চ" row
        mm_row = None
        for r in range(header_rows[0] + 1, min(header_rows[0] + 4, len(grid))):
            if any("সর্বনিম্ন" in txt(v) for v in grid[r]):
                mm_row = grid[r]
                break
        groups = {}
        for g in ("today", "week", "month", "year"):
            if g not in cols:
                continue
            c = cols[g]
            mn, mx = c, c + 1
            if mm_row:
                mins = [i for i, v in enumerate(mm_row) if i >= c and "সর্বনিম্ন" in txt(v)]
                maxs = [i for i, v in enumerate(mm_row) if i >= c and "সর্ব" in txt(v)
                        and "চ্চ" in txt(v)]
                if mins:
                    mn = mins[0]
                if maxs:
                    mx = maxs[0]
            groups[g] = (mn, mx)
    else:
        layout = "default (no header found)"
        cols = {"name": 0, "unit": 1}
        groups = {"today": (2, 3), "week": (4, 5), "month": (6, 7), "year": (9, 10)}
        header_rows = [-1]

    if "today" not in groups:
        raise ValueError("could not find 'today price' column")
    name_c = cols.get("name", 0)
    unit_c = cols.get("unit", name_c + 1)

    d, date_src = find_date(grid, header_rows[0] if header_rows[0] >= 0 else None,
                            groups["today"][0])
    if d is None:
        raise ValueError("could not find the report date")

    serial = ""
    markets = ""
    for row in grid[:8]:
        line = " ".join(txt(x) for x in row if x is not None)
        m = re.search(r"সিরিয়াল\s*নং\s*[ঃ:]?\s*([০-৯\d]+)", unicodedata.normalize("NFC", line))
        if m:
            serial = m.group(1).translate(BN_DIGITS)

    records = []
    category = "Rice"
    start = header_rows[0] + 1
    for r in range(start, len(grid)):
        row = grid[r]
        name = txt(cell(row, name_c))
        row_text = " ".join(txt(x) for x in row if x is not None)
        if "যে সকল বাজার" in row_text:
            markets = " ".join(txt(x) for x in row[1:] if txt(x))
            break
        if "মন্তব্য" in row_text or "যে সকল পণ্যের" in row_text:
            break
        if not name or "পণ্যের নাম" in name:
            continue
        is_mm_row = any("সর্বনিম্ন" in txt(v) for v in row)
        prices = {g: (to_price(cell(row, a)), to_price(cell(row, b)))
                  for g, (a, b) in groups.items()}
        has_any_number = any(isinstance(cell(row, i), (int, float))
                             for g in groups.values() for i in g)
        unit_bn = txt(cell(row, unit_c))
        if is_mm_row or (not has_any_number and not unit_bn):
            cat = CATEGORY_LOOKUP.get(norm(name))
            category = cat if cat else translate_product(name)[0]
            continue
        en, cat, status = translate_product(name)
        tmin, tmax = prices["today"]
        records.append({
            "Date": d,
            "Category": cat or category,
            "Product": en,
            "Unit": translate_unit(unit_bn),
            "Price_Min": tmin,
            "Price_Max": tmax,
            "Price_Avg": avg(tmin, tmax),
            "Week_Ago_Min": prices.get("week", (None, None))[0],
            "Week_Ago_Max": prices.get("week", (None, None))[1],
            "Month_Ago_Min": prices.get("month", (None, None))[0],
            "Month_Ago_Max": prices.get("month", (None, None))[1],
            "Year_Ago_Min": prices.get("year", (None, None))[0],
            "Year_Ago_Max": prices.get("year", (None, None))[1],
            "Product_Bangla": " ".join(name.split()),
            "Unit_Bangla": unit_bn,
            "Translation": status,
            "Serial_No": serial,
        })
    if not records:
        raise ValueError("no price rows found")
    return records, {"date": d, "date_source": date_src, "layout": layout,
                     "serial": serial, "markets_bn": markets}


def avg(a, b):
    vals = [x for x in (a, b) if x is not None]
    if not vals:
        return None
    m = sum(vals) / len(vals)
    return int(m) if float(m).is_integer() else round(m, 2)


# =====================================================================
# 4. MINIMAL XLSX WRITER (built-in libraries only)
# =====================================================================
_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/><numFmt numFmtId="165" formatCode="#,##0.##"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def write_sheet(zf, path, headers, rows, widths):
    with zf.open(path, "w") as f:
        w = lambda s: f.write(s.encode("utf-8"))
        last = col_letter(len(headers) - 1)
        w('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
          'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>')
        for i, wd in enumerate(widths):
            w(f'<col min="{i+1}" max="{i+1}" width="{wd}" customWidth="1"/>')
        w('</cols><sheetData>')
        w('<row r="1" ht="30" customHeight="1">')
        for i, h in enumerate(headers):
            w(f'<c r="{col_letter(i)}1" t="inlineStr" s="1"><is><t>{escape(h)}</t></is></c>')
        w('</row>')
        epoch = date(1899, 12, 30)
        for rn, row in enumerate(rows, start=2):
            parts = [f'<row r="{rn}">']
            for i, v in enumerate(row):
                if v is None or v == "":
                    continue
                ref = f"{col_letter(i)}{rn}"
                if isinstance(v, date):
                    parts.append(f'<c r="{ref}" s="2"><v>{(v - epoch).days}</v></c>')
                elif isinstance(v, (int, float)):
                    parts.append(f'<c r="{ref}"><v>{v}</v></c>')
                else:
                    s = escape(_BAD_XML.sub("", str(v)))
                    parts.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{s}</t></is></c>')
            parts.append("</row>")
            w("".join(parts))
        w(f'</sheetData><autoFilter ref="A1:{last}{max(1, len(rows) + 1)}"/></worksheet>')


def write_xlsx(path, sheets):
    """sheets = list of (name, headers, rows, widths)"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        defined = []
        for i, (name, headers, rows, widths) in enumerate(sheets, start=1):
            write_sheet(zf, f"xl/worksheets/sheet{i}.xml", headers, rows, widths)
            ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
            wb.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
            rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
            last = col_letter(len(headers) - 1)
            defined.append(f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i-1}" hidden="1">'
                           f"'{escape(name)}'!$A$1:${last}${max(1, len(rows) + 1)}</definedName>")
        n = len(sheets) + 1
        rels.append(f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
        wb.append("</sheets><definedNames>" + "".join(defined) + "</definedNames></workbook>")
        ct.append("</Types>")
        rels.append("</Relationships>")
        zf.writestr("[Content_Types].xml", "".join(ct))
        zf.writestr("_rels/.rels",
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                    '</Relationships>')
        zf.writestr("xl/workbook.xml", "".join(wb))
        zf.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        zf.writestr("xl/styles.xml", STYLES_XML)


# =====================================================================
# 5. MAIN
# =====================================================================
PRICE_COLS = ["Date", "Year", "Month", "Weekday", "Category", "Product", "Unit",
              "Price_Min", "Price_Max", "Price_Avg",
              "Week_Ago_Min", "Week_Ago_Max", "Month_Ago_Min", "Month_Ago_Max",
              "Year_Ago_Min", "Year_Ago_Max",
              "Product_Bangla", "Unit_Bangla", "Translation", "Serial_No", "Source_File"]
PRICE_WIDTHS = [12, 7, 7, 10, 15, 36, 18, 10, 10, 10, 11, 11, 12, 12, 11, 11, 30, 18, 11, 9, 44]


def _pause(msg="\nPress Enter to close..."):
    if PAUSE:
        input(msg)


PAUSE = True


def main(in_folder=None, out_xlsx=None, out_csv=None, pause=True):
    global PAUSE, OUTPUT_XLSX, OUTPUT_CSV
    PAUSE = pause
    if out_xlsx: OUTPUT_XLSX = out_xlsx
    if out_csv: OUTPUT_CSV = out_csv
    in_folder = in_folder or (sys.argv[1] if len(sys.argv) > 1 else INPUT_FOLDER)
    if not os.path.isdir(in_folder):
        print(f"Folder not found: {in_folder}")
        _pause()
        return
    load_user_translations()

    files = sorted(f for f in os.listdir(in_folder)
                   if f.lower().endswith((".xlsx", ".xls", ".xlsm")) and not f.startswith("~$"))
    print(f"Found {len(files)} Excel file(s) in {in_folder}\n")

    all_records, log, seen_dates = [], [], {}
    for n, fname in enumerate(files, 1):
        path = os.path.join(in_folder, fname)
        status, reason, info, recs = "FAILED", "", {}, []
        try:
            if fname.lower().endswith(".xls"):
                raise ValueError("old .xls format - open in Excel and 'Save As' .xlsx, then rerun")
            sheets = read_xlsx(path)
            errors = []
            for grid in sheets:
                try:
                    recs, info = parse_tcb_sheet(grid)
                    break
                except ValueError as e:
                    errors.append(str(e))
            if not recs:
                raise ValueError("; ".join(errors) or "no sheets")
            d = info["date"]
            if d in seen_dates:
                status = "DUPLICATE"
                reason = f"same date as {seen_dates[d]} - skipped"
                recs = []
            else:
                seen_dates[d] = fname
                status = "OK"
                if info["layout"] != "detected":
                    reason = "layout guessed - please spot-check"
        except zipfile.BadZipFile:
            reason = "not a real .xlsx file (corrupt or HTML error page)"
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"

        for r in recs:
            r["Source_File"] = fname
        all_records.extend(recs)
        log.append([fname, status, info.get("date"), len(recs), info.get("serial", ""),
                    info.get("date_source", ""), reason, info.get("markets_bn", "")])
        if n % 50 == 0 or status != "OK":
            print(f"[{n}/{len(files)}] {status:9} {fname} {reason}")

    if not all_records:
        print("\nNo data extracted. See reasons above.")
        _pause()
        return

    all_records.sort(key=lambda r: (r["Date"], r["Category"], r["Product"], r["Unit"]))
    price_rows = []
    for r in all_records:
        d = r["Date"]
        r["Year"], r["Month"], r["Weekday"] = d.year, d.month, d.strftime("%A")
        price_rows.append([r.get(c) for c in PRICE_COLS])

    # Wide sheet: one row per date, one column per product+unit (average price)
    items = sorted({(r["Category"], r["Product"], r["Unit"]) for r in all_records})
    item_idx = {it: i for i, it in enumerate(items)}
    by_date = {}
    for r in all_records:
        by_date.setdefault(r["Date"], [None] * len(items))[
            item_idx[(r["Category"], r["Product"], r["Unit"])]] = r["Price_Avg"]
    wide_headers = ["Date"] + [f"{p} | {u}" if u else p for _, p, u in items]
    wide_rows = [[d] + vals for d, vals in sorted(by_date.items())]

    # Untranslated names
    untrans = {}
    for r in all_records:
        if r["Translation"] != "exact":
            k = (r["Product_Bangla"], r["Translation"], r["Product"])
            untrans[k] = untrans.get(k, 0) + 1
    un_rows = [[bn, st, en, c] for (bn, st, en), c in
               sorted(untrans.items(), key=lambda x: -x[1])]

    sheets = [
        ("Prices", PRICE_COLS, price_rows, PRICE_WIDTHS),
        ("Wide_Avg_Price", wide_headers, wide_rows, [12] + [18] * len(items)),
        ("Files_Log", ["File", "Status", "Report_Date", "Rows", "Serial_No",
                       "Date_Found_From", "Note", "Markets_Surveyed (Bangla)"],
         log, [44, 11, 12, 7, 9, 18, 50, 60]),
        ("Untranslated", ["Bangla_Name", "Status", "Current_English", "Rows"],
         un_rows, [40, 10, 40, 8]),
    ]
    try:
        write_xlsx(OUTPUT_XLSX, sheets)
    except PermissionError:
        print(f"\nCannot write {OUTPUT_XLSX} - close it in Excel and run again.")
        _pause()
        return
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(PRICE_COLS)
        for row in price_rows:
            wr.writerow(["" if v is None else (v.isoformat() if isinstance(v, date) else v)
                         for v in row])

    ok = sum(1 for l in log if l[1] == "OK")
    dup = sum(1 for l in log if l[1] == "DUPLICATE")
    fail = sum(1 for l in log if l[1] == "FAILED")
    print("\n================ SUMMARY ================")
    print(f"Files OK        : {ok}")
    print(f"Duplicates      : {dup}  (same report date, skipped)")
    print(f"Files FAILED    : {fail}  (see Files_Log sheet)")
    print(f"Price rows      : {len(price_rows)}")
    print(f"Dates covered   : {wide_rows[0][0]} to {wide_rows[-1][0]}  ({len(wide_rows)} days)")
    print(f"Distinct items  : {len(items)}")
    print(f"Untranslated    : {sum(1 for u in un_rows if u[1] == 'missing')} names "
          f"(+{sum(1 for u in un_rows if u[1] == 'auto')} auto-translated) - see Untranslated sheet")
    print(f"\nSaved: {OUTPUT_XLSX}\nSaved: {OUTPUT_CSV}")
    _pause()


if __name__ == "__main__":
    # Project use (added 2026-11-15; everything above is the user's converter, unchanged):
    #   python tools/tcb_convert.py --in FOLDER --out-csv OUT.csv [--out-xlsx OUT.xlsx]
    # With no options it behaves as before (reads Downloads/TCB_Daily_RMP, writes to Downloads, waits for Enter).
    if any(a.startswith("--") for a in sys.argv[1:]):
        import argparse
        ap = argparse.ArgumentParser(description="TCB daily Bangla Excel reports -> one English CSV")
        ap.add_argument("--in", dest="in_folder", required=True, help="folder with the downloaded .xlsx reports")
        ap.add_argument("--out-csv", required=True, help="CSV to write (must not exist)")
        ap.add_argument("--out-xlsx", help="formatted Excel copy (default: next to the CSV)")
        a = ap.parse_args()
        out_xlsx = a.out_xlsx or os.path.splitext(a.out_csv)[0] + ".xlsx"
        for f in (a.out_csv, out_xlsx):
            if os.path.exists(f):
                sys.exit(f"STOP: {f} already exists; choose a new name (earlier files are never overwritten).")
        main(a.in_folder, out_xlsx, a.out_csv, pause=False)
    else:
        main()
