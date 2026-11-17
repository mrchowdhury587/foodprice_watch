"""Builds the thesis files that contain TCB prices, for upload to Overleaf only (never to git).

Writes into DATA_ROOT/reports/thesis_upload/ (Drive in Colab, FW_DATA_ROOT locally):
  tables/data_sample.tex     a few rows of data_8.csv for one report day (dataset sample, Ch. 3)
  tables/worked_example.tex  one sustained rise followed day by day under the ML range (sample input and output, Ch. 4)
  figures/F2_*.png, F5_*.png copied from reports/figures
Upload the two folders into report_v5/ in Overleaf. Run: python tools/thesis_upload.py [item] [onset date]
"""
import shutil
import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from foodwatch import paths as P  # noqa: E402

ITEM = sys.argv[1] if len(sys.argv) > 1 else "Onion - Local"
ONSET = sys.argv[2] if len(sys.argv) > 2 else "2025-11-02"
OUT = P.DATA_ROOT / "reports" / "thesis_upload"
(OUT / "tables").mkdir(parents=True, exist_ok=True)
(OUT / "figures").mkdir(parents=True, exist_ok=True)


def tk(x):
    return "--" if pd.isna(x) else f"{x:.1f}"


# ---- dataset sample: all 8 items on the first report day of the test period
D = pd.read_csv(P.data("data"), parse_dates=["Date"])
day = D[D.Date >= "2025-01-01"].Date.min()
s = D[D.Date == day].sort_values("item_id")
rows = []
for _, x in s.iterrows():
    it, unit = x.item_id.split(" | ")
    rows.append(f"{it} & {unit} & {tk(x.Price_Min)} & {tk(x.Price_Max)} & {tk(x.Price_Avg)} & {int(x.report_idx)} & "
                f"{int(x.reports_since_change) if pd.notna(x.reports_since_change) else '--'} & "
                f"{'--' if pd.isna(x.fx_ch30) else f'{x.fx_ch30:.4f}'} & {'--' if pd.isna(x.wx_tmax_7d) else f'{x.wx_tmax_7d:.1f}'} \\\\")
(OUT / "tables" / "data_sample.tex").write_text(
    "\\begin{tabular}{llrrrrrrr}\n\\toprule\n"
    "\\textbf{Item} & \\textbf{Unit} & \\textbf{Min} & \\textbf{Max} & \\textbf{Avg} & \\textbf{report\\_idx} & "
    "\\textbf{since change} & \\textbf{fx\\_ch30} & \\textbf{wx\\_tmax\\_7d} \\\\\n\\midrule\n"
    + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n"
    f"% report day {day.date()}\n", encoding="utf-8")

# ---- worked example: one sustained rise, day by day, under the ML range (rule A)
M = pd.read_csv(P.data("monitor"), parse_dates=["date"])
E = pd.read_csv(P.data("rise_episodes"), parse_dates=["onset_date", "end_date"])
it = [i for i in M.item_id.unique() if i.startswith(ITEM)][0]
e = E[(E.item_id == it) & (E.onset_date == pd.Timestamp(ONSET))].iloc[0]
m = M[M.item_id == it].sort_values("report_idx")
starts = m[m.run_start_A & m.report_idx.between(e.onset_idx - 14, e.end_idx + 7)]
first = int(starts.report_idx.iloc[0]) if len(starts) else int(e.onset_idx)
w = m[m.report_idx.between(e.onset_idx - 3, first + 2)]
rows = []
for _, x in w.iterrows():
    st = "ALERT" if x.alert_A else (f"above on {x.days_above_A} of 5" if x.days_above_A > 0 else "normal")
    if x.run_start_A:
        st = "\\textbf{ALERT starts}"
    mark = " (onset)" if x.report_idx == e.onset_idx else ""
    rows.append(f"{x.date.date()}{mark} & {tk(x.price_7_ago)} & {tk(x.price)} & {100 * x.change_7:+.1f} & {tk(x.bound_A)} & "
                f"{'yes' if x.exceed_A else 'no'} & {x.days_above_A} & {st} \\\\")
(OUT / "tables" / "worked_example.tex").write_text(
    "\\begin{tabular}{lrrrrlrl}\n\\toprule\n"
    "\\textbf{Report day} & \\textbf{Price $t-7$} & \\textbf{Price $t$} & \\textbf{Change (\\%)} & \\textbf{Bound A} & "
    "\\textbf{Above} & \\textbf{Days above (of 5)} & \\textbf{Status} \\\\\n\\midrule\n"
    + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

# ---- price figures
for f in ("F2_prices_with_rises.png", "F5_prices_with_alerts.png"):
    src = P.DATA_ROOT / "reports" / "figures" / f
    if src.exists():
        shutil.copy2(src, OUT / "figures" / f)

# Printed summary: dates and counts only (no prices), safe to paste back
print("dataset sample day:", day.date())
print(f"worked example: {ITEM}, onset {e.onset_date.date()}, end {e.end_date.date()}, "
      f"{int(e.length_reports)} report days, peak rise {100 * e.peak_rise:.0f} %")
print("ML range alert run starts:", m[m.report_idx == first].date.dt.date.iloc[0], "| delay", first - int(e.onset_idx), "report days")
print("written to", OUT, ":", sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*.*")))
