"""S30 Production fit and exports. One LightGBM fitted on every usable report day; forecasts for the latest origin at 1/7/14/30 report days with the expected
range (each item's last 120 forecast errors of the test period at the level fixed in S28). Files (Drive only, they hold prices): outputs/export/forecasts.parquet,
alerts.csv, alert_drivers.csv (S29) and models/lgbm_production.txt."""
import sys, json
sys.path.insert(0, "src")
import numpy as np, pandas as pd, yaml
from fpw.io import ROOT
from fpw.project import PCFG, features_path, out_dir
from fpw import ml, register, state
state.start("S30")
tun = json.loads((ROOT / "state/tuning_S26.json").read_text()); params = dict(tun["params"], num_threads=2); n = int(tun["n_estimators"])
lvl = float(yaml.safe_load((ROOT / "state/prereg_S28.yaml").read_text(encoding="utf-8"))["chosen_level"])
F = pd.read_parquet(features_path()); S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
dates = F.drop_duplicates("report_idx").set_index("report_idx").Date; last = int(dates.index.max()); win = int(PCFG["alerts"]["window"])
model = ml.fit(L, last, cols, params, n)
model.save_model(str(out_dir("models") / "lgbm_production.txt"))
O = ml.origin_rows(L, last); pred = model.predict(O[cols])
fc = ml.to_forecast(O, pred, "lgbm").drop(columns=["actual", "y", "model"])
T = pd.read_parquet(ROOT / "outputs/27_test/forecasts_test.parquet"); T = T[T.y.notna()].assign(resid=lambda x: x.y - x.pred).sort_values("cutoff")
g = T.groupby(["item_id", "horizon"]).resid
q = pd.DataFrame(dict(hi=g.apply(lambda r: r.tail(win).quantile(lvl)), lo=g.apply(lambda r: r.tail(win).quantile(1 - lvl)))).reset_index()
fc = fc.merge(q, on=["item_id", "horizon"], how="left")
fc["forecast_high"] = np.exp(fc.lp_origin + fc.pred + fc.hi); fc["forecast_low"] = np.exp(fc.lp_origin + fc.pred + fc.lo)
fc["origin_date"] = fc.cutoff.map(dates); fc["last_price"] = np.exp(fc.lp_origin); fc["range_level"] = lvl
fc = fc[["item_id", "eval_stratum", "origin_date", "horizon", "last_price", "forecast", "forecast_low", "forecast_high", "range_level"]]
ex = out_dir("exports"); fc.to_parquet(ex / "forecasts.parquet", index=False)
pd.read_csv(ROOT / "outputs/28_alerts/alerts.csv").to_csv(ex / "alerts.csv", index=False)
register.section("S30", "S30 production export", "python -m fpw.runner S30", ["outputs/export/forecasts.parquet"],
                 [("items forecast", int(fc.item_id.nunique())), ("forecast rows", int(len(fc))), ("latest origin", str(fc.origin_date.max().date())), ("range level", lvl),
                  ("rows without a range", int(fc.forecast_high.isna().sum()))])
print(fc.groupby("horizon").agg(items=("item_id", "nunique"), no_range=("forecast_high", lambda s: int(s.isna().sum()))).to_string()); print(fc.head(8).to_string())
