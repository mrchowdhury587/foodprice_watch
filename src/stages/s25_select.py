"""S25 Model selection on the validation year (idempotent, resumable per candidate). Candidates: config/project.yaml selection.candidates.
Scored on 2024 rolling origins only; the 2025-26 test is not touched. Outputs: P5_selection.csv, state/selection_S25.json, outputs/25_select/forecasts_<model>.parquet.
Winner = lowest mean log-change MAE over horizons; a simpler model within tie_margin wins; 'naive' is the reference and never chosen."""
import sys, json, time, hashlib
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import ROOT
from fpw.project import PCFG, features_path, need, out_dir
from fpw.checkpoint import run_unit, sha256
from fpw import ml, cv, candidates as C, metrics as M, state
state.start("S25")
names = list(need("selection", "candidates")); margin = float(need("selection", "tie_margin")); refit = int(need("test", "refit_every_n_cutoffs"))
F = pd.read_parquet(features_path())
S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date
cut = cv.validation_year_cutoffs(dates)
print(f"validation origins: {len(cut)} ({cut[0]}..{cut[-1]}), dates {dates[cut[0]].date()}..{dates[cut[-1]].date()}", flush=True)
assert max(cut) + 30 <= dates.index[dates <= pd.Timestamp(PCFG["validation"]["confirm"][1])].max()
assert max(cut) < int(PCFG["test"]["first_cutoff"]), "validation origins reach the test period"
d = ROOT / "outputs/25_select"; d.mkdir(parents=True, exist_ok=True)
cfg_hash = hashlib.sha256(json.dumps(PCFG, sort_keys=True, default=str).encode()).hexdigest()[:16]
fcs = {}
for m in names:
    out = d / f"forecasts_{m}.parquet"; t0 = time.time()
    r = run_unit(out, lambda m=m: C.run_candidate(m, S, L, cols, cut, refit_every=refit), inputs={"features": features_path().name, "origins": len(cut)}, config_hash=cfg_hash, seed=42)
    fcs[m] = pd.read_parquet(out); print(f"{m}: {r} in {time.time()-t0:.0f}s, rows {len(fcs[m])}", flush=True)
ref = fcs.get("naive")
rows = []
for m, fc in fcs.items():
    s = M.summary(fc, by=["horizon"]); g = M.gmean_rel(fc)
    s = s.merge(g, on="horizon")
    s.insert(0, "model", m); rows.append(s)
T = pd.concat(rows, ignore_index=True)
overall = T.groupby("model").agg(mae_log=("mae_log", "mean"), mae_tk=("mae_tk", "mean"), gmean_rel_mae=("gmean_rel_mae", "mean")).reset_index()
scores = dict(zip(overall.model, overall.mae_log))
winner = C.choose_winner(scores, margin)
T.to_csv(out_dir("tables") / "P5_selection.csv", index=False)
overall.to_csv(out_dir("tables") / "P5_selection_overall.csv", index=False)
rec = dict(rule=f"lowest mean log-change MAE over horizons {PCFG['horizons']} on the 2024 rolling origins; a simpler model within {margin:.0%} wins; naive is the reference",
           origins=len(cut), first_origin=int(cut[0]), last_origin=int(cut[-1]), scores={k: float(v) for k, v in scores.items()}, winner=winner, candidates=names,
           naive_mae_log=float(T[T.model == "naive"].mae_log.mean()) if "naive" in names else None,
           winner_beats_naive=bool(scores[winner] < float(T[T.model == "naive"].mae_log.mean())) if "naive" in names else None,
           chosen_at=time.strftime("%Y-%m-%dT%H:%M:%S"), features_sha256=sha256(features_path()))
(ROOT / "state").mkdir(exist_ok=True); (ROOT / "state/selection_S25.json").write_text(json.dumps(rec, indent=2))
print(json.dumps(rec, indent=1)); print(overall.round(5).to_string()); print(T.pivot(index="model", columns="horizon", values="gmean_rel_mae").round(3).to_string())
if winner != "lgbm":
    print(f"NOTE: the validation winner is {winner}, not lgbm. S26-S29 are built for the LightGBM pipeline: ask the user before continuing.")
