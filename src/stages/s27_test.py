"""S27 Sealed test (once) and full evaluation. The pre-registration state/prereg_S27.yaml must be committed in the repo first (from the work PC);
this stage verifies it against the copy S26 wrote to Drive, unseals the 2025-26 test exactly once, scores it, and writes tables, figures and register rows.
Outputs: P7_*.csv, figures F10-F14, outputs/27_test/forecasts_*.parquet (Drive only: they hold prices), RESULTS_REGISTER section."""
import sys, json, time, hashlib
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import ROOT
from fpw.paths import CODE_ROOT
from fpw.project import PCFG, features_path, out_dir
from fpw.checkpoint import run_unit, unseal_test, sha256
from fpw import ml, cv, metrics as M, evaluate as E, prereg, register, state
state.start("S27")
PRE = CODE_ROOT / "state/prereg_S27.yaml"
sel = json.loads((ROOT / "state/selection_S25.json").read_text()); tun = json.loads((ROOT / "state/tuning_S26.json").read_text())
assert PRE.exists(), "STOP: state/prereg_S27.yaml is not in the repo. Commit and push it from the work PC, then re-run (README: seal handoff)."
prereg.verify_s27(PRE, ROOT / "state/prereg_S27.yaml", sel, tun)
status = unseal_test("S27", PRE, seal_dir=ROOT / "state/seals")          # refuses if the file is not committed or the test was already unsealed once
print("seal:", status, flush=True)

F = pd.read_parquet(features_path()); S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
import yaml
assert cols == yaml.safe_load(PRE.read_text(encoding="utf-8"))["features"], "the feature list differs from the pre-registration"
params = dict(tun["params"], num_threads=2); n = int(tun["n_estimators"]); refit = int(PCFG["test"]["refit_every_n_cutoffs"])
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date
cal = F.drop_duplicates("report_idx").set_index("report_idx")[["in_ramadan", "days_to_eid_fitr", "days_to_eid_adha"]]
strata = S[["item_id", "eval_stratum"]].drop_duplicates()
d = ROOT / "outputs/27_test"; d.mkdir(parents=True, exist_ok=True)
cfg_hash = hashlib.sha256(PRE.read_bytes()).hexdigest()[:16]
test_cuts = cv.test_cutoffs(); assert len(test_cuts) == 87
meta = dict(inputs={"features": features_path().name, "prereg_sha256": sha256(PRE)}, config_hash=cfg_hash, seed=42)


def unit(name, cutoffs, window=None):
    out = d / f"forecasts_{name}.parquet"
    def compute():
        if window is None:
            return ml.forecasts(L, cutoffs, cols, refit_every=refit, params=params, n_estimators=n, model_name="lgbm")
        fit_fn = lambda L_, c, cols_: ml.fit(L_[L_.report_idx > c - window], c, cols_, params, n)
        return ml.forecasts(L, cutoffs, cols, refit_every=refit, model_name="lgbm", fit_fn=fit_fn)
    t0 = time.time(); r = run_unit(out, compute, **meta); print(f"{name}: {r} ({time.time()-t0:.0f}s)", flush=True)
    return pd.read_parquet(out)

# main test, in blocks of one refit each so a dropped session resumes
blocks = [test_cuts[i:i + refit] for i in range(0, len(test_cuts), refit)]
parts = [unit(f"test_block{i:02d}", b) for i, b in enumerate(blocks)]
test = pd.concat(parts, ignore_index=True); test.to_parquet(d / "forecasts_test.parquet", index=False)
wf = cv.walk_forward_cutoffs(dates, (2023, 2024))
schemes = {"rolling origin 2025-26 (main)": test, "walk-forward 2023": unit("wf2023", wf[2023]), "walk-forward 2024 (tuning year)": unit("wf2024", wf[2024]),
           "sliding window 500 reports, 2025-26": unit("sliding500", test_cuts, window=500)}

scale = M.mase_scale(L, test_cuts[0])
T = out_dir("tables"); H = E.by_horizon(test, strata); G = E.by_group(test, strata); I = E.by_item(test, scale)
tagged = E.tag(test, dates, cal); EA = E.error_analysis(tagged); W = E.worst(tagged); DM = M.dm_vs_naive(test); B = E.bias_over_time(tagged)
WF = pd.concat([E.by_horizon(fc, strata).assign(scheme=k) for k, fc in schemes.items()], ignore_index=True)
curve = E.learning_curve(L, test_cuts[0], cols, params, n)
for name, t in [("P7_accuracy_by_horizon", H), ("P7_accuracy_by_group", G), ("P7_accuracy_by_item", I), ("P7_walk_forward", WF), ("P7_error_analysis", EA),
                ("P7_worst20", W), ("P7_dm_vs_naive", DM), ("P7_learning_curve", curve), ("P7_bias_over_time", B)]:
    t.to_csv(T / f"{name}.csv", index=False)
figs = E.figures(tagged, H, curve, B, out_dir("figures"))
beats = bool((H.gmean_rel_mae < 1).all())
rows = []
for r in H.itertuples():
    rows += [(f"h={r.horizon}: mean absolute error of the log price change", float(r.mae_log), "P7_accuracy_by_horizon.csv"), (f"h={r.horizon}: error relative to tomorrow = today (geometric mean over items)", float(r.gmean_rel_mae), "P7_accuracy_by_horizon.csv"),
             (f"h={r.horizon}: mean absolute error in Tk", float(r.mae_tk), "P7_accuracy_by_horizon.csv"), (f"h={r.horizon}: direction accuracy on days the price moved", float(r.direction_acc), "P7_accuracy_by_horizon.csv"),
             (f"h={r.horizon}: bias in Tk (forecast - actual)", float(r.bias_tk), "P7_accuracy_by_horizon.csv")]
for r in DM.itertuples():
    rows.append((f"h={r.horizon}: Diebold-Mariano p-value vs tomorrow = today (supporting evidence)", float(r.p_value), "P7_dm_vs_naive.csv"))
rows += [("test origins", len(test_cuts), "P7_accuracy_by_horizon.csv"), ("scored forecasts", int(len(M.scored(test))), "P7_accuracy_by_horizon.csv"),
         ("model beats tomorrow = today at every horizon (relative error < 1)", str(beats), "P7_accuracy_by_horizon.csv")]
register.section("S27", "S27 sealed test and evaluation (2025-01 to 2026-10, 87 origins)", "python -m fpw.runner S27", ["reports/project/tables/P7_accuracy_by_horizon.csv"], rows)
print(H.round(4).to_string()); print(WF[["scheme", "horizon", "mae_log", "gmean_rel_mae"]].round(4).to_string()); print(DM.round(4).to_string())
print("model beats tomorrow = today at every horizon:", beats, "| figures:", [p.name for p in figs])
