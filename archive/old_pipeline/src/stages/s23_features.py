"""S23 Features of the prediction system (idempotent). Output: features_v2.parquet, outputs/23_features/checks.json, P3_driver_inventory.csv.
Kept drivers only: calendar, weather (the 2024 choice, not re-chosen), India onion export measures, exchange rate.
The earlier feature table (features.parquet, S04) is not touched."""
import sys, json, yaml
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import panel, ROOT
from fpw.project import PCFG, features_path, out_dir
from fpw.checkpoint import sha256
from fpw import drivers as D, state, features as FT
state.start("S23")
fc = PCFG["features"]; MAP = yaml.safe_load((ROOT / "config/item_driver_map.yaml").read_text(encoding="utf-8"))
assert set(fc["weather"]) <= set(FT.WEATHER_CANDIDATES), fc["weather"]
p = panel(version=2)
wraw = D.weather(); fxraw = D.fx()
F = FT.build(p, D.events("bd_ramadan_eid.csv"), D.events("bd_public_holidays_2019_2027.csv").date, wraw, fxraw, D.events("exporter_policy_events.csv"),
             weather_cols=fc["weather"], weather_items=MAP["G5_weather"], weather_lag_days=fc["weather_lag_days"],
             export_items=MAP["G3_export_measure"], fx_strata=fc["fx_strata"], cap_days=fc["carry_cap_days"])
assert len(F) == len(p) and not F.duplicated(["Date", "item_id"]).any()
OUT = features_path(); tmp = OUT.with_suffix(".parquet.tmp"); F.to_parquet(tmp, index=False); tmp.replace(OUT)
def last_filled(col):
    x = F[F[col].notna()]; return str(x.Date.max().date()) if len(x) else None
last = F.Date.max(); tail = F[F.Date == last]
chk = dict(rows=len(F), items=int(F.item_id.nunique()), date_min=str(F.Date.min().date()), date_max=str(last.date()), columns=list(F.columns),
           weather_chosen=fc["weather"], weather_items=int(F.loc[F.has_weather == 1].item_id.nunique()), export_items=int(F.loc[F.has_export_measure == 1].item_id.nunique()),
           fx_items=int(F.loc[F.has_fx == 1].item_id.nunique()),
           weather_source_last_day=str(wraw.time.max().date()), fx_source_last_day=str(fxraw.date.max().date()),
           weather_last_report_day_filled=last_filled("weather_1"), fx_last_report_day_filled=last_filled("fx_lvl"), export_last_report_day_known=last_filled("own_export_measure"),
           # drivers that are empty on the latest report day although the item uses them (stale source files): reported, not hidden
           latest_day_weather_empty=int((tail.has_weather.eq(1) & tail.weather_1.isna()).sum()), latest_day_fx_empty=int((tail.has_fx.eq(1) & tail.fx_lvl.isna()).sum()),
           output_sha256=sha256(OUT))
(ROOT / "outputs/23_features").mkdir(parents=True, exist_ok=True)
(ROOT / "outputs/23_features/checks.json").write_text(json.dumps(chk, indent=2))
inv = [("price history", "built at model time from the panel: log changes, deviation from the rolling mean, volatility, reports since change", "report day", "none", "all"),
       ("calendar", ", ".join(FT.CAL), "daily, known ahead", "0", "all"),
       ("weather", ", ".join(fc["weather"]) + " (chosen on 2024 by the earlier run)", "daily", f"+{fc['weather_lag_days']} d, carried at most {fc['carry_cap_days']} d", f"{chk['weather_items']} items"),
       ("onion export measures", "own_export_measure: 1 while an Indian onion duty, minimum price or ban is in force", "event", "start date; empty outside the table's coverage", f"{chk['export_items']} items"),
       ("exchange rate", "fx_lvl (log BDT per USD), fx_ch30 (change over 30 days)", "daily", f"last value on or before the report day, carried at most {fc['carry_cap_days']} d", f"{chk['fx_items']} items")]
T = pd.DataFrame(inv, columns=["group", "features", "frequency", "availability", "items"])
T["last_report_day_with_a_value"] = ["", str(last.date()), chk["weather_last_report_day_filled"], chk["export_last_report_day_known"], chk["fx_last_report_day_filled"]]
T.to_csv(out_dir("tables") / "P3_driver_inventory.csv", index=False)
print("S23 unit: features"); print(json.dumps({k: v for k, v in chk.items() if k != "columns"}, indent=1)); print(T.drop(columns="features").to_string())
