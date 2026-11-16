"""S22 Panel on the extended price file (idempotent). Outputs tcb_v2_rebuilt.parquet, outputs/22_panel/checks.json, P2_panel_summary.csv.
The earlier panel (tcb_v1.0_rebuilt.parquet) and S01 are not touched. Stops if any date up to base_last_date differs from the base file."""
import sys, json
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import raw, item_meta, PROC, CFG, ROOT
from fpw.project import PCFG, price_csv, panel_path, out_dir
from fpw.checkpoint import sha256
from fpw import state, panel as P
state.start("S22")
src = price_csv()
if not src.exists():
    sys.exit(f"STOP: {src.name} is not in data/raw/project/. Put it in inbox/project/ and re-run the S00 intake cell (docs/DATA_COLLECTION.md).")
base_src = raw("tcb_dhaka_daily_prices_2021_2026.csv"); last = PCFG["base_last_date"]
new_raw = pd.read_csv(src, parse_dates=["Date"]); base_raw = pd.read_csv(base_src, parse_dates=["Date"])
assert list(new_raw.columns) == list(base_raw.columns), "column layout differs from the base price file"
n_diff = P.same_as_base(new_raw, base_raw, last, [c for c in base_raw.columns if c not in ("Date", "Product", "Unit")])
assert n_diff == 0, f"{n_diff} cell(s) on dates up to {last} differ from the base file: the extended file must only ADD report days"
cand = pd.read_csv(raw("audit_candidates.csv"))
ck = set(zip(pd.to_datetime(cand[[c for c in cand.columns if "date" in c.lower()][0]]), cand[[c for c in cand.columns if "item" in c.lower()][0]]))
df = P.build(new_raw, item_meta(), ck, CFG["gap_2022"])
# the first report days keep their index, so the 87 test origins (808..1410) mean the same days as in the earlier run
base_dates = sorted(base_raw.Date.unique())
idx = df.drop_duplicates("Date").set_index("Date").report_idx
assert (idx.loc[base_dates].values == np.arange(len(base_dates))).all(), "report_idx of earlier report days changed"
OUT = panel_path(); tmp = OUT.with_suffix(".parquet.tmp"); df.to_parquet(tmp, index=False); tmp.replace(OUT)
(PROC / (OUT.stem + ".sha256")).write_text(sha256(OUT) + "  " + OUT.name + "\n")
chk = P.checks(df)
new_days = sorted(d for d in df.Date.unique() if d > pd.Timestamp(last))
chk.update(source_file=src.name, source_sha256=sha256(src), base_last_date=last, cells_differing_from_base=n_diff, base_rows=len(base_raw), base_dates=len(base_dates),
           new_report_days=len(new_days), first_new_day=str(pd.Timestamp(new_days[0]).date()) if new_days else None, rows_added=len(df) - len(base_raw),
           new_days_rows_min=int(df[df.Date > last].groupby("Date").size().min()) if new_days else None,
           new_days_reported_share=round(float(df.loc[df.Date > last, "is_reported"].mean()), 4) if new_days else None, output_sha256=sha256(OUT))
(ROOT / "outputs/22_panel").mkdir(parents=True, exist_ok=True)
(ROOT / "outputs/22_panel/checks.json").write_text(json.dumps(chk, indent=2, default=str))
assert chk["dup_keys"] == 0 and chk["avg_mid_violations"] == 0 and chk["min_gt_max"] == 0 and chk["zero_or_negative"] == 0, chk
assert chk["gap_2022_reports"] == 24 and chk["items"] == 63 and chk["week_ago_match_share"] >= 0.995, chk
# P2 panel summary (same columns as the earlier T1, for the longer sample)
rows = []
for st, g in df.groupby("eval_stratum"):
    per = g.groupby("item_id")
    unchanged = per.apply(lambda x: (x.Price_Avg.dropna().diff().dropna() == 0).mean())
    rows.append(dict(eval_stratum=st, n_series=g.item_id.nunique(), report_days=g.Date.nunique(), share_unchanged_median=round(unchanged.median(), 3),
                     share_missing=round(g.Price_Avg.isna().mean(), 4), first_report=str(per.apply(lambda x: x.loc[x.Price_Avg.notna(), "Date"].min()).min().date()),
                     last_report=str(g.loc[g.Price_Avg.notna(), "Date"].max().date())))
T = pd.DataFrame(rows); T.to_csv(out_dir("tables") / "P2_panel_summary.csv", index=False)
print("S22 unit: panel"); print(json.dumps(chk, indent=1, default=str)); print(T.to_string())
