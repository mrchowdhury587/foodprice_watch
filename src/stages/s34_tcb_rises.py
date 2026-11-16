"""S34 Alerts judged against an independent TCB price-rise reference (docs/PROJECT_DESIGN_DRAFT.md section 12). No model is refitted, no bound is changed.
Rise rule (config/project.yaml `rises`, written to state/prereg_S34.yaml): R = P_t / P_(t-14 report days) - 1 >= 10 %, kept for 5 report days; sensitivity at 7 % and 15 %.
A) rise counts on the validation year 2024 (stops if there are too few episodes to judge anything).
B) the prereg file must be committed in the repo; then the 2024 and the 2025-26 periods are scored (2025-26 is retrospective: it was already scored by the earlier model).
Alert runs come from outputs/28_alerts/forecasts_daily.parquet at the level fixed in state/prereg_S28.yaml."""
import sys
sys.path.insert(0, "src")
import numpy as np, pandas as pd, yaml
from fpw.io import ROOT
from fpw.paths import CODE_ROOT
from fpw.project import PCFG, features_path, out_dir
from fpw.checkpoint import unseal_test
from fpw import prereg, register, alerts as A, rises as R, state
state.start("S34")
r = PCFG["rises"]; w, persist, mgap = int(r["window_reports"]), int(r["persist_reports"]), int(r["merge_gap_reports"])
before, after = int(r["match"]["before_reports"]), int(r["match"]["after_reports"]); main_thr = float(r["threshold"])
thrs = [main_thr] + [float(x) for x in r["sensitivity"]]
level = float(yaml.safe_load((ROOT / "state/prereg_S28.yaml").read_text(encoding="utf-8"))["chosen_level"])
F = pd.read_parquet(features_path()); dates = F.drop_duplicates("report_idx").set_index("report_idx").Date
fd = pd.read_parquet(ROOT / "outputs/28_alerts/forecasts_daily.parquet").sort_values(["item_id", "cutoff"]).reset_index(drop=True)
items = sorted(fd.item_id.unique()); F = F[F.item_id.isin(items)]
stratum = fd.drop_duplicates("item_id").set_index("item_id").eval_stratum
col = f"alert{level}"; Hh = int(fd.horizon.iloc[0])
runs_all = A.episodes(fd, col)[["item_id", "cutoff"]].assign(start_idx=lambda x: x.cutoff + Hh)[["item_id", "start_idx"]]
idx_of = lambda d: int(dates[dates >= pd.Timestamp(d)].index.min()); idx_le = lambda d: int(dates[dates <= pd.Timestamp(d)].index.max())
PER = {"validation_2024": r["validation"], "retrospective_2025_26": r["retrospective"]}
EPS = {t: R.episodes(R.rise_days(F, w, t), persist, mgap) for t in thrs}
for t in thrs:
    EPS[t]["onset_date"] = EPS[t].onset_idx.map(dates); EPS[t]["end_date"] = EPS[t].end_idx.map(dates); EPS[t]["stratum"] = EPS[t].item_id.map(stratum)


def in_period(idx, p):
    return (idx >= idx_of(PER[p][0])) & (idx <= idx_le(PER[p][1]))


T = out_dir("tables")
cnt = pd.concat([EPS[t][in_period(EPS[t].onset_idx, "validation_2024")].groupby("stratum").size().rename(f"rise_episodes_2024_at_{int(t * 100)}pct") for t in thrs], axis=1).fillna(0).astype(int)
cnt.loc["all items"] = cnt.sum(); cnt.to_csv(T / "P10_rise_counts_2024.csv"); print(cnt.to_string(), flush=True)
n_main = int(cnt.loc["all items"].iloc[0])
if n_main < int(r["min_validation_episodes"]):
    print(f"STOP: only {n_main} rise episodes on 2024 at {main_thr:.0%}; the rule cannot be judged. Tell the user; any change needs a DEVIATIONS.md entry first.", flush=True); sys.exit(4)

text = prereg.s34(level); (ROOT / "state/prereg_S34.yaml").write_text(text, encoding="utf-8")
repo_pre = CODE_ROOT / "state/prereg_S34.yaml"
if not repo_pre.exists() or repo_pre.read_text(encoding="utf-8") != text:
    print("STOP: commit this file as state/prereg_S34.yaml in the repo (work PC), push, then re-run this stage.\n----\n" + text + "----", flush=True); sys.exit(3)
print("seal:", unseal_test("S34", repo_pre, seal_dir=ROOT / "state/seals"), flush=True)

rows, grows, ep_out = [], [], []
for t in thrs:
    for p in PER:
        e = EPS[t][in_period(EPS[t].onset_idx, p)]; rn = runs_all[in_period(runs_all.start_idx, p)]
        e_m, r_m = R.match(rn, e, before, after); s = R.prf(e_m, r_m)
        pl = R.placebo(rn, e, before, after, idx_of(PER[p][0]), idx_le(PER[p][1]), int(r["placebo_draws"]))
        rows.append(dict(threshold=t, period=p, **s, placebo_mean_recall=pl["placebo_mean"], placebo_p=pl["placebo_p"]))
        if t == main_thr:
            ep_out.append(e_m.assign(period=p))
            for g, eg in e_m.groupby("stratum"):
                grows.append(dict(period=p, stratum=g, **R.prf(eg, r_m[r_m.item_id.map(stratum) == g])))
S = pd.DataFrame(rows); G = pd.DataFrame(grows); E = pd.concat(ep_out)
E[["item_id", "stratum", "period", "onset_date", "end_date", "peak_R", "detected", "delay_reports"]].to_csv(T / "P10_rise_episodes.csv", index=False)
S.to_csv(T / "P10_alerts_vs_rises.csv", index=False); G.to_csv(T / "P10_alerts_vs_rises_by_group.csv", index=False)
m = S[(S.threshold == main_thr)].set_index("period")
register.section("S34", "S34 alerts judged against TCB price rises (rule fixed in state/prereg_S34.yaml; 2025-26 is retrospective)", "python -m fpw.runner S34",
                 ["reports/project/tables/P10_alerts_vs_rises.csv"],
                 [(f"{p}: {k}", float(m.loc[p, k]) if k not in ("episodes", "detected", "alert_runs", "matched_runs") else int(m.loc[p, k]), "P10_alerts_vs_rises.csv")
                  for p in PER for k in ("episodes", "detected", "recall", "alert_runs", "matched_runs", "precision", "f1", "median_delay_reports", "placebo_p")])
print(S.round(3).to_string()); print(G.round(3).to_string())
