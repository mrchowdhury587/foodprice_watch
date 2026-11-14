"""tools/tcb_append.py on a small made-up file (standard library only; no project data needed)."""
import csv, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
H = ["Date", "Category", "Product", "Unit", "Price_Min", "Price_Max", "Price_Avg", "Week_Ago_Min", "Week_Ago_Max", "Month_Ago_Min", "Month_Ago_Max",
     "Year_Ago_Min", "Year_Ago_Max", "Product_Bangla", "Unit_Bangla", "Serial_No"]
CONV = ["Date", "Year", "Month", "Weekday"] + H[1:14] + ["Unit_Bangla", "Translation", "Serial_No", "Source_File"]
def row(date, lo, hi, product="Potato"):
    return dict(Date=date, Category="Vegetables", Product=product, Unit="per kg", Price_Min=lo, Price_Max=hi, Price_Avg=(float(lo) + float(hi)) / 2,
                Week_Ago_Min=lo, Week_Ago_Max=hi, Month_Ago_Min="", Month_Ago_Max="", Year_Ago_Min="", Year_Ago_Max="", Product_Bangla="x", Unit_Bangla="y", Serial_No="7")
def write(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="ignore", restval=""); w.writeheader(); w.writerows(rows)
def run(*args):
    return subprocess.run([sys.executable, str(R / "tools/tcb_append.py"), *map(str, args)], capture_output=True, text=True)
def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8", newline="")))
def conv(r):
    return dict(r, Year=r["Date"][:4], Month="1", Weekday="Monday", Translation="exact", Source_File="a.xlsx")
def setup(tmp_path, base_rows, new_rows):
    write(tmp_path / "base.csv", H, base_rows); write(tmp_path / "new.csv", CONV, [conv(r) for r in new_rows])
    return tmp_path / "base.csv", tmp_path / "new.csv", tmp_path / "out.csv"
def test_converter_layout_and_date_cut(tmp_path):
    base_rows = [dict(row("2026-01-01", "20.0", "24.0"), Serial_No="7.0", Price_Avg="22.0", Week_Ago_Min="20.0", Week_Ago_Max="24.0"),
                 dict(row("2026-01-02", "30.0", "34.0"), Serial_No="7.0", Price_Avg="32.0", Week_Ago_Min="30.0", Week_Ago_Max="34.0")]   # 01-02 holds a hand correction
    b, n, o = setup(tmp_path, base_rows, [row("2026-01-01", 20, 24), row("2026-01-02", 20, 26), row("2026-01-03", 21, 25)])
    r = run("--base", b, "--new", n, "--out", o, "--after-last-base-date"); assert r.returncode == 0, r.stdout + r.stderr
    out = read(o)
    assert list(out[0]) == H and [x["Date"] for x in out] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert out[:2] == read(b), "base rows changed"
    assert out[2]["Price_Min"] == "21.0" and out[2]["Price_Avg"] == "23.0" and out[2]["Serial_No"] == "7.0" and out[2]["Month_Ago_Min"] == ""
def test_conflict_stops_without_the_date_cut(tmp_path):
    b, n, o = setup(tmp_path, [dict(row("2026-01-02", "30.0", "34.0"), Price_Avg="32.0")], [row("2026-01-02", 20, 26), row("2026-01-03", 21, 25)])
    r = run("--base", b, "--new", n, "--out", o); assert r.returncode != 0 and "conflict" in r.stdout and not o.exists()
def test_bad_price_and_unknown_series_stop(tmp_path):
    b, n, o = setup(tmp_path, [row("2026-01-01", "20.0", "24.0")], [row("2026-01-02", 26, 20), row("2026-01-02", 5, 6, product="Mango")])
    r = run("--base", b, "--new", n, "--out", o, "--after-last-base-date")
    assert r.returncode != 0 and "Min > Max" in r.stdout and "unknown series" in r.stdout and not o.exists()
def test_never_overwrites(tmp_path):
    b, n, o = setup(tmp_path, [row("2026-01-01", "20.0", "24.0")], [row("2026-01-02", 21, 25)]); o.write_text("keep")
    r = run("--base", b, "--new", n, "--out", o); assert r.returncode != 0 and o.read_text() == "keep"
