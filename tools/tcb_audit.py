"""
Audit the price CSV against the original TCB Excel reports (work PC; needs openpyxl).

    python tools/tcb_audit.py --prices PRICES.csv --sample audit_sample_2pct.csv --candidates audit_candidates.csv
                              --originals Downloads/TCB_Daily_RMP --out-dir reports/project/tables

For every sampled (Date, item) it opens the Excel file named in the sample, finds the row by its Bangla
product name and unit, reads today's minimum and maximum price (the two cells after the unit) and compares
them with the CSV. It does not use tools/tcb_convert.py: the Excel file is read with openpyxl and the row is
found by the Bangla text, so a parsing or translation mistake in the converter would show up here.

This is a machine re-read of the originals. It measures transcription (file -> CSV) accuracy. It cannot tell
whether TCB itself typed a wrong number; such values stay flagged (audit candidates), never changed.

Writes P2_audit.csv (one line per checked value) and P2_audit_summary.csv. Never overwrites the inputs.
"""
import argparse, csv, datetime as dt, math, os, re, sys, unicodedata, warnings

BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def norm(s):
    s = unicodedata.normalize("NFC", "" if s is None else str(s)).replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", "", s)


def number(v):
    """Cell -> float, or None for blank / zero / text (TCB writes 0 or leaves the cell empty when a price is not reported)."""
    if v is None or isinstance(v, bool): return None
    if isinstance(v, (int, float)): x = float(v)
    else:
        t = str(v).translate(BN).replace(",", "").strip()
        try: x = float(t)
        except ValueError: return None
    return None if x == 0 or math.isnan(x) else x


def csvnum(s):
    s = (s or "").strip()
    return float(s) if s else None


def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 1e-9)


def wilson(k, n, z=1.959964):
    if n == 0: return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


class Originals:
    def __init__(self, folder):
        import openpyxl
        self.x, self.folder, self.cache = openpyxl, folder, {}

    def sheet(self, fname):
        if fname not in self.cache:
            path = os.path.join(self.folder, fname)
            if not os.path.exists(path): self.cache[fname] = None
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    wb = self.x.load_workbook(path, data_only=True)
                self.cache[fname] = [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]
        return self.cache[fname]

    @staticmethod
    def has_date(grid, want):
        if any(isinstance(c, (dt.datetime, dt.date)) and (c.date() if isinstance(c, dt.datetime) else c) == want for r in grid[:12] for c in r):
            return True
        head = norm(" ".join(str(c) for r in grid[:8] for c in r if c is not None)).translate(BN)   # older sheets: date only as Bangla text
        return re.search(rf"(?<!\d)0?{want.day}(?!\d)", head) is not None and str(want.year) in head

    def lookup(self, fname, date, product_bn, unit_bn):
        """-> (min, max, note). note is '' when the row was found once and the sheet carries the expected date.
        A workbook may hold spare sheets: the sheet whose heading carries the report date is used, else the first one."""
        sheets = self.sheet(fname)
        if sheets is None: return None, None, "original file not found"
        want = dt.date.fromisoformat(date)
        with_date = [g for g in sheets if self.has_date(g, want)]
        grid, dated = (with_date[0], True) if with_date else (sheets[0], False)
        hits = [r for r in grid if len(r) >= 4 and norm(r[0]) == norm(product_bn) and norm(r[1]) == norm(unit_bn)]
        if not hits: return None, None, "row not found by Bangla name and unit"
        # the sheet ends with a list of items whose price changed (a sentence in the 8th cell); the price table has only numbers there
        table = [r for r in hits if not any(isinstance(c, str) and c.strip() for c in r[2:8])]
        hits = table or hits
        note = "" if dated else "sheet date not confirmed"
        if len(hits) > 1:
            vals = {(number(r[2]), number(r[3])) for r in hits}
            if len(vals) > 1: return None, None, f"{len(hits)} rows with this name and unit, different prices"
        return number(hits[0][2]), number(hits[0][3]), note


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prices", required=True); ap.add_argument("--sample", required=True); ap.add_argument("--candidates")
    ap.add_argument("--corrections", help="corrections.csv: sampled values changed by hand on purpose are labelled, not counted as errors")
    ap.add_argument("--originals", required=True); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--with-values", action="store_true", help="also write the prices of matching cells (keep such a file out of git)")
    a = ap.parse_args()
    prices = {(r["Date"], r["Product"] + " | " + r["Unit"]): r for r in read(a.prices)}
    corrected = {(r["Date"], r["item_id"]) for r in read(a.corrections)} if a.corrections else set()
    orig = Originals(a.originals)
    out = []
    jobs = [("sample", r) for r in read(a.sample)] + ([("candidate", r) for r in read(a.candidates)] if a.candidates else [])
    for kind, s in jobs:
        key = (s["Date"], s["item_id"]); p = prices.get(key)
        if p is None:
            out.append(dict(kind=kind, Date=s["Date"], item_id=s["item_id"], field="", csv_value="", original_value="", result="not checked",
                            note="row not in the price CSV", source_file=s["Source_File"])); continue
        lo, hi, note = orig.lookup(s["Source_File"], s["Date"], p["Product_Bangla"], p["Unit_Bangla"])
        found = not note or note == "sheet date not confirmed"
        for field, o in (("Price_Min", lo), ("Price_Max", hi)):
            c = csvnum(p[field])
            if not found: res = "not checked"
            elif same(c, o): res = "match"
            elif key in corrected: res = "hand correction"
            else: res = "MISMATCH"
            n2 = note
            if kind == "sample" and not same(csvnum(s[field]), c): n2 = (n2 + "; " if n2 else "") + "CSV value differs from the value stored in the sample file"
            show = res != "match" or a.with_values          # the repo is public and TCB reuse terms are unconfirmed: prices only where they differ
            out.append(dict(kind=kind, Date=s["Date"], item_id=s["item_id"], field=field, csv_value="" if c is None or not show else c,
                            original_value="" if o is None or not show else o, result=res, note=n2, source_file=s["Source_File"]))
    os.makedirs(a.out_dir, exist_ok=True)
    cols = ["kind", "Date", "item_id", "field", "csv_value", "original_value", "result", "note", "source_file"]
    with open(os.path.join(a.out_dir, "P2_audit.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(out)

    S = [r for r in out if r["kind"] == "sample"]
    def rows_of(rs):                                                     # one sampled row = Min and Max of one (Date, item)
        d = {}
        for r in rs: d.setdefault((r["Date"], r["item_id"]), []).append(r["result"])
        return d
    R = rows_of(S); checked = {k: v for k, v in R.items() if "not checked" not in v}
    bad_rows = sum("MISMATCH" in v for v in checked.values())
    cells = [r for r in S if r["result"] != "not checked"]; bad_cells = sum(r["result"] == "MISMATCH" for r in cells)
    lo_r, hi_r = wilson(bad_rows, len(checked)); lo_c, hi_c = wilson(bad_cells, len(cells))
    summ = [("sampled rows (date x item)", len(R)), ("report days in the sample", len({k[0] for k in R})), ("rows checked against the original file", len(checked)),
            ("rows not checked (file or row not found)", len(R) - len(checked)), ("rows with a mismatch", bad_rows),
            ("row error rate", round(bad_rows / len(checked), 5) if checked else ""), ("row error rate, Wilson 95% low", round(lo_r, 5)), ("row error rate, Wilson 95% high", round(hi_r, 5)),
            ("price cells checked (Min and Max)", len(cells)), ("price cells with a mismatch", bad_cells),
            ("cell error rate", round(bad_cells / len(cells), 5) if cells else ""), ("cell error rate, Wilson 95% low", round(lo_c, 5)), ("cell error rate, Wilson 95% high", round(hi_c, 5)),
            ("cells that are hand corrections (not errors)", sum(r["result"] == "hand correction" for r in S)),
            ("rows where the sheet date could not be confirmed", len({(r["Date"], r["item_id"]) for r in S if "sheet date not confirmed" in r["note"]})),
            ("rows where the CSV differs from the stored sample value", len({(r["Date"], r["item_id"]) for r in S if "stored in the sample" in r["note"]}))]
    for (d, it), v in rows_of([r for r in out if r["kind"] == "candidate"]).items():
        dec = "not checked" if "not checked" in v else ("CSV differs from the original file" if "MISMATCH" in v else "CSV equals the original TCB file: value kept, stays flagged")
        summ.append((f"candidate {d} {it}", dec))
    with open(os.path.join(a.out_dir, "P2_audit_summary.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["measure", "value"]); w.writerows(summ)
    for k, v in summ: print(f"{k:58} {v}")
    for r in [r for r in out if r["result"] == "MISMATCH"][:20]:
        sys.stdout.buffer.write((f"MISMATCH {r['kind']} {r['Date']} {r['item_id']} {r['field']}: csv {r['csv_value']} original {r['original_value']} ({r['source_file']})\n").encode("utf-8"))


if __name__ == "__main__":
    main()
