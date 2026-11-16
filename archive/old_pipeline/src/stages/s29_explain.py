"""S29 Driver breakdown. LightGBM's own additive contributions (pred_contrib, the same quantity SHAP reports for trees) are summed by driver group
(price history, calendar, weather, onion export measures, exchange rate). Levels: overall, by horizon, by item group, by item, and for each alert.
Also sign checks and stability across refits. Wording: a rise the drivers do not account for is "not explained by measured cost drivers"."""
import sys, json
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import ROOT
from fpw.project import PCFG, features_path, out_dir
from fpw import ml, register, state
state.start("S29")
tun = json.loads((ROOT / "state/tuning_S26.json").read_text()); params = dict(tun["params"], num_threads=2); n = int(tun["n_estimators"])
F = pd.read_parquet(features_path()); S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns(); grp = ml.group_of(cols)
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date; last = int(dates.index.max()); H = int(PCFG["alerts"]["horizon"])
groups = sorted(set(grp.values()))


def contrib(model, X):
    """(contributions summed by driver group + baseline, contributions per feature) for the rows of X."""
    c = model.predict(X[cols], pred_contrib=True)
    G = pd.DataFrame({g: c[:, [i for i, k in enumerate(cols) if grp[k] == g]].sum(axis=1) for g in groups}, index=X.index); G["baseline"] = c[:, -1]
    return G, pd.DataFrame(c[:, :-1], columns=cols, index=X.index)


models = {c: ml.fit(L, c, cols, params, n) for c in (last - 400, last - 200, last)}
model = models[last]
rows = L[(L.report_idx > last - 120) & (L.report_idx <= last) & L.lp.notna() & ~L.touch_gap]
G, Fc = contrib(model, rows); T = out_dir("tables")


def share(g):
    m = g[groups].abs().mean(); return (m / m.sum()).rename("share")


def tidy(frames, key):
    return pd.concat([share(g).to_frame().assign(**{key: k}) for k, g in frames]).reset_index().rename(columns={"index": "driver_group"})


overall = share(G).reset_index().rename(columns={"index": "driver_group"}); overall.to_csv(T / "P9_driver_overall.csv", index=False)
tidy([(h, G[rows.horizon.values == h]) for h in sorted(rows.horizon.unique())], "horizon").to_csv(T / "P9_driver_by_horizon.csv", index=False)
tidy([(s, G[rows.eval_stratum.values == s]) for s in sorted(rows.eval_stratum.unique())], "eval_stratum").to_csv(T / "P9_driver_by_item_group.csv", index=False)
G.abs().groupby(rows.item_id.values)[groups].mean().reset_index().rename(columns={"index": "item_id"}).to_csv(T / "P9_driver_by_item.csv", index=False)
chk = []
for f_, expect in [("dev30", "negative or about zero (mean reversion)"), ("fx_ch30", "non-negative for import-linked items")]:
    if f_ in cols:
        x = rows[f_]; ok = x.notna().values
        chk.append(dict(feature=f_, expected=expect, corr_with_contribution=float(np.corrcoef(x[ok], Fc.loc[ok, f_])[0, 1]) if ok.sum() > 10 else np.nan))
pd.DataFrame(chk).to_csv(T / "P9_sign_checks.csv", index=False)
stab = pd.DataFrame({f"refit_{c}": share(contrib(m, rows)[0]) for c, m in models.items()}); stab["spread"] = stab.max(axis=1) - stab.min(axis=1)
stab.reset_index().rename(columns={"index": "driver_group"}).to_csv(T / "P9_driver_stability.csv", index=False)

# per alert: the expected change and each group's part of it at the alert's origin (horizon H)
ex = ROOT / "outputs/export"; ex.mkdir(parents=True, exist_ok=True)
D = pd.read_parquet(ROOT / "outputs/28_alerts/forecasts_daily.parquet")
alert_col = [c for c in D.columns if c.startswith("alert")][0]
st = D[D[alert_col].fillna(False).astype(bool)].copy()
O = L[L.horizon == H].set_index(["item_id", "report_idx"]); O = O[~O.index.duplicated()]
keys = [k for k in zip(st.item_id, st.cutoff) if k in O.index]
X = O.loc[keys]
GA, _ = contrib(model, X) if len(X) else (pd.DataFrame(columns=groups + ["baseline"]), None)
GA.index = pd.MultiIndex.from_tuples(keys, names=["item_id", "cutoff"]) if len(X) else GA.index
out = st.set_index(["item_id", "cutoff"]).join(GA, how="left").reset_index()
out["expected_change_log"] = out[groups + ["baseline"]].sum(axis=1)
out["not_explained_by_measured_cost_drivers_log"] = out.resid
out["note"] = "the part of the rise above the expected range is not explained by measured cost drivers"
out.to_csv(ex / "alert_drivers.csv", index=False)
register.section("S29", "S29 driver breakdown", "python -m fpw.runner S29", ["reports/project/tables/P9_driver_overall.csv"],
                 [(f"share of the forecast change from {r.driver_group}", float(r.share), "P9_driver_overall.csv") for r in overall.itertuples()] +
                 [("largest spread of a group share across three refits", float(stab.spread.max()), "P9_driver_stability.csv"), ("alert days explained", int(len(out)), "outputs/export/alert_drivers.csv")])
print(overall.round(3).to_string()); print(stab.round(3).to_string()); print(pd.DataFrame(chk).to_string()); print("alert days:", len(out))
