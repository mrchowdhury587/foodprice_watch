"""S28 Ranges and alerts on daily rolling forecasts (horizon from config alerts.horizon). Two phases, one script:
A) forecast every report day, build ranges, choose the alert level on 2024 outside the event windows, write state/prereg_S28.yaml to Drive.
   If the repo has no identical committed copy the stage stops here and prints the file: commit it from the work PC, then re-run.
B) unseal "S28" and score the 12 shock episodes (recall, lead days, precision, false alarms, placebo) and range quality. Events never influence the level."""
import sys, json, hashlib
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import ROOT
from fpw.paths import CODE_ROOT, RAW
from fpw.project import PCFG, features_path, out_dir
from fpw.checkpoint import run_unit, unseal_test, sha256
from fpw import ml, prereg, register, alerts as A, state
state.start("S28")
a = PCFG["alerts"]; H = int(a["horizon"]); levels = list(a["levels"]); K, M_ = int(a["persistence"]["k"]), int(a["persistence"]["m"])
tun = json.loads((ROOT / "state/tuning_S26.json").read_text()); params = dict(tun["params"], num_threads=2); n = int(tun["n_estimators"])
F = pd.read_parquet(features_path()); S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date
start = int(dates[dates >= pd.Timestamp(a["eval_start"])].index.min())
last = int(dates.index.max()); refit = int(a["refit_every"])
d = ROOT / "outputs/28_alerts"; d.mkdir(parents=True, exist_ok=True)
L7 = L[L.horizon == H]
meta = dict(inputs={"features": features_path().name, "tuning": sha256(ROOT / "state/tuning_S26.json")}, config_hash=hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()[:16], seed=42)
cuts = list(range(start - 130, last + 1)); blocks = [cuts[i:i + refit] for i in range(0, len(cuts), refit)]
fit_fn = lambda L_, c, cols_: ml.fit(L, c, cols_, params, n)
parts = []
for i, b in enumerate(blocks):
    out = d / f"fc_block{i:03d}.parquet"
    run_unit(out, lambda b=b: ml.forecasts(L7, b, cols, refit_every=len(b), model_name="lgbm", fit_fn=fit_fn), **meta); parts.append(pd.read_parquet(out))
fc = pd.concat(parts, ignore_index=True); fc["tdate"] = fc.target_idx.map(dates)
P = A.bounds(fc, H, levels, int(a["window"]), int(a["min_obs"])); P = P[P.tdate.notna()].reset_index(drop=True); P = A.flag_alerts(P, levels, K, M_)
P = P[P.cutoff >= start].reset_index(drop=True)
prod = F.drop_duplicates("item_id").assign(product=lambda x: x["Product"] if "Product" in x else x.item_id.str.split(" | ", regex=False).str[0]).set_index("item_id")["product"]
by_prod = prod.groupby(prod).groups; by_prod = {k: list(v) for k, v in by_prod.items()}
ev = A.load_events(RAW / "shock_events.csv"); W = A.windows(ev, by_prod, int(a["event_window_days"]["before_onset"]), int(a["event_window_days"]["after_peak"]))
level, rule, fa = A.choose_level(P, levels, W, float(a["fa_target_per_item_year"]), "2024-01-01", "2024-12-31")
text = prereg.s28(dict(level=level, rule=rule, fa_by_level=fa))
drive_pre = ROOT / "state/prereg_S28.yaml"; drive_pre.write_text(text, encoding="utf-8")
repo_pre = CODE_ROOT / "state/prereg_S28.yaml"
if not repo_pre.exists() or repo_pre.read_text(encoding="utf-8") != text:
    print("STOP: commit this file as state/prereg_S28.yaml in the repo (work PC), push, then re-run this stage.\n----\n" + text + "----", flush=True); sys.exit(3)
print("seal:", unseal_test("S28", repo_pre, seal_dir=ROOT / "state/seals"), flush=True)

col = f"alert{level}"; T = out_dir("tables"); P["date"] = P.tdate
s = A.score_events(P, col, W, ev); pr, n_runs = A.precision(P, col, W); pl = A.placebo(P, col, W, ev)
curve = pd.DataFrame([dict(level=lv, false_alarms_per_item_year_2024=fa[str(lv)], event_recall=A.score_events(P, f"alert{lv}", W, ev).detected.mean(),
                           precision=A.precision(P, f"alert{lv}", W)[0], alert_runs=A.precision(P, f"alert{lv}", W)[1]) for lv in levels])
rq = A.range_quality(P, level, by=("horizon",)); rq_item = A.range_quality(P.assign(period=np.where(P.tdate < "2025-01-01", "2023-24", "2025-26")), level, by=("period",))
s.to_csv(T / "P8_event_scores.csv", index=False); curve.to_csv(T / "P8_level_curve.csv", index=False); rq.to_csv(T / "P8_range_quality.csv", index=False)
rq_item.to_csv(T / "P8_range_quality_by_period.csv", index=False); pd.DataFrame([dict(pl, precision=pr, alert_runs=n_runs, level=level)]).to_csv(T / "P8_alert_summary.csv", index=False)
keep = ["item_id", "eval_stratum", "cutoff", "tdate", "horizon", "forecast", "actual", "resid", f"hi{level}", f"lo{level}", f"exceed{level}", col]
P[keep].to_parquet(d / "forecasts_daily.parquet", index=False)
A.episodes(P, col)[["item_id", "tdate", "forecast", "actual", "resid", f"hi{level}"]].to_csv(d / "alerts.csv", index=False)
register.section("S28", "S28 ranges and alerts (shock episodes scored once)", "python -m fpw.runner S28", ["reports/project/tables/P8_event_scores.csv"],
                 [("alert level (upper bound quantile)", float(level), "state/prereg_S28.yaml"), ("false alarms per item-year, 2024 non-event", float(fa[str(level)]), "P8_level_curve.csv"),
                  ("events detected", int(s.detected.sum()), "P8_event_scores.csv"), ("events scored", int(len(s)), "P8_event_scores.csv"),
                  ("share of alert runs inside an event window", pr, "P8_alert_summary.csv"), ("alert runs", n_runs, "P8_alert_summary.csv"),
                  ("placebo p-value (random dates)", pl["placebo_p"], "P8_alert_summary.csv"), ("placebo mean recall", pl["placebo_mean"], "P8_alert_summary.csv"),
                  ("upper-bound coverage", float(rq.upper_coverage.iloc[0]), "P8_range_quality.csv"), ("Kupiec p-value", float(rq.kupiec_p.iloc[0]), "P8_range_quality.csv")])
print(s.to_string()); print(curve.round(3).to_string()); print(rq.round(3).to_string()); print(pl)
