"""S26 Optuna tuning of the LightGBM winner (idempotent, resumable). Tune on Jan-Sep 2024, confirm on Oct-Dec 2024; if the tuned setting loses its edge
on the confirm period the simpler default setting is kept. All trials are saved. Writes P6_tuning_trials.csv, state/tuning_S26.json and state/prereg_S27.yaml.
Trials are written to Drive after every trial; a restart re-loads them instead of repeating them. The test period is never touched."""
import sys, json, time
sys.path.insert(0, "src")
import numpy as np, pandas as pd, optuna
from fpw.io import ROOT
from fpw.project import PCFG, features_path, need, out_dir
from fpw.checkpoint import sha256
from fpw import ml, cv, metrics as M, prereg, state
optuna.logging.set_verbosity(optuna.logging.WARNING)
state.start("S26")
sel = json.loads((ROOT / "state/selection_S25.json").read_text())
if sel["winner"] != "lgbm":
    sys.exit(f"STOP: the validation winner is {sel['winner']}; S26-S29 are built for LightGBM. Ask the user before continuing.")
trials_n = int(need("tuning", "trials")); refit = int(need("test", "refit_every_n_cutoffs")); sp = need("tuning", "search")
F = pd.read_parquet(features_path()); S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date
tcut, ccut = cv.tune_cutoffs(dates), cv.confirm_cutoffs(dates)
assert max(tcut) < min(ccut) and max(ccut) < int(PCFG["test"]["first_cutoff"])
print(f"tune origins {len(tcut)} ({dates[tcut[0]].date()}..{dates[tcut[-1]].date()}), confirm origins {len(ccut)} ({dates[ccut[0]].date()}..{dates[ccut[-1]].date()})", flush=True)

D = optuna.distributions
SPACE = dict(num_leaves=D.IntDistribution(*sp["num_leaves"]), learning_rate=D.FloatDistribution(*sp["learning_rate"], log=True),
             objective=D.CategoricalDistribution(sp["objective"]), min_data_in_leaf=D.IntDistribution(20, 200),
             feature_fraction=D.FloatDistribution(0.5, 1.0), bagging_fraction=D.FloatDistribution(0.5, 1.0),
             lambda_l1=D.FloatDistribution(0.0, 10.0), lambda_l2=D.FloatDistribution(0.0, 10.0), n_estimators=D.IntDistribution(100, 600, step=50))


def split(p):
    p = dict(p); n = int(p.pop("n_estimators")); return p, n


def score(params, n, cuts):
    fc = ml.forecasts(L, cuts, cols, refit_every=refit, params=params, n_estimators=n)
    return float(M.summary(fc, by=["horizon"]).mae_log.mean())


def suggest(trial, k, d):
    if isinstance(d, D.CategoricalDistribution): return trial.suggest_categorical(k, d.choices)
    if isinstance(d, D.IntDistribution): return trial.suggest_int(k, d.low, d.high, step=d.step)
    return trial.suggest_float(k, d.low, d.high, log=d.log)


def objective(trial):
    p = {k: suggest(trial, k, d) for k, d in SPACE.items()}
    t0 = time.time(); q, n = split(p); q["num_threads"] = 2
    v = score(q, n, tcut); trial.set_user_attr("seconds", round(time.time() - t0, 1)); return v


TR = out_dir("tables") / "P6_tuning_trials.csv"
(ROOT / "outputs/26_tune").mkdir(parents=True, exist_ok=True); CK = ROOT / "outputs/26_tune/trials_checkpoint.csv"
study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
if CK.exists():
    old = pd.read_csv(CK)
    for _, r in old.iterrows():
        params = {k: (int(r[k]) if isinstance(d, D.IntDistribution) else (str(r[k]) if isinstance(d, D.CategoricalDistribution) else float(r[k]))) for k, d in SPACE.items()}
        study.add_trial(optuna.trial.create_trial(params=params, distributions=SPACE, value=float(r["value"]), user_attrs={"seconds": float(r["seconds"])}))
    print(f"resumed {len(old)} trials", flush=True)


def save(study, trial=None):
    df = study.trials_dataframe(attrs=("number", "value", "params", "user_attrs")).rename(columns=lambda c: c.replace("params_", "").replace("user_attrs_", ""))
    df.to_csv(CK, index=False)
    print(f"trial {len(df)}/{trials_n}: value {df['value'].iloc[-1]:.5f} best {df['value'].min():.5f} ({df['seconds'].iloc[-1]}s)", flush=True)


todo = trials_n - len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
if todo > 0:
    study.optimize(objective, n_trials=todo, callbacks=[save])
trials = pd.read_csv(CK); trials.to_csv(TR, index=False)
best = study.best_trial; bp, bn = split(best.params); bp["num_threads"] = 2
dp = dict(ml.PARAMS); dn = ml.N_ESTIMATORS
tune_best, tune_def = score(bp, bn, tcut), score(dp, dn, tcut)
conf_best, conf_def = score(bp, bn, ccut), score(dp, dn, ccut)
keep_tuned = conf_best < conf_def
chosen, cn = (bp, bn) if keep_tuned else (dp, dn)
chosen = {k: v for k, v in chosen.items() if k not in ("verbose", "seed", "num_threads", "bagging_freq")}
rule = ("tuned setting kept: it is better than the default on the Oct-Dec 2024 confirm period" if keep_tuned else
        "default (simpler) setting kept: the tuned setting lost its edge on the Oct-Dec 2024 confirm period")
clean = lambda v: float(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v)
rec = dict(params={k: clean(v) for k, v in sorted(chosen.items())}, n_estimators=int(cn), rule=rule, trials=int(len(trials)),
           tune_score=dict(tuned=tune_best, default=tune_def), confirm_score=dict(tuned=conf_best, default=conf_def),
           tuned_params={k: clean(v) for k, v in best.params.items()},
           tune_origins=[int(tcut[0]), int(tcut[-1]), len(tcut)], confirm_origins=[int(ccut[0]), int(ccut[-1]), len(ccut)])
(ROOT / "state/tuning_S26.json").write_text(json.dumps(rec, indent=2, sort_keys=True))
(ROOT / "state/prereg_S27.yaml").write_text(prereg.s27(sel, rec), encoding="utf-8")
print(json.dumps(rec, indent=1, sort_keys=True))
print("prereg_S27.yaml sha256", sha256(ROOT / "state/prereg_S27.yaml"))
print("tuning_S26.json sha256", sha256(ROOT / "state/tuning_S26.json"))
print(trials.sort_values("value").head(8).round(5).to_string())
