"""S23: driver features. Part 1 checks each rule on small made-up inputs (runs anywhere); part 2 checks the real table (where S23 has run)."""
import json
from pathlib import Path
import pytest
pd = pytest.importorskip("pandas"); np = pytest.importorskip("numpy")
import yaml
from fpw import features as FT
from fpw.paths import ROOT as R, CODE_ROOT
PC = yaml.safe_load((CODE_ROOT / "config/project.yaml").read_text(encoding="utf-8")); fc = PC["features"]
OUT = R / "data/processed" / PC["features_file"]
ts = pd.Timestamp

# ---------- part 1: rules on made-up inputs
def test_asof_never_uses_a_later_value_and_respects_the_cap():
    dates = pd.DataFrame({"Date": pd.to_datetime(["2024-01-05", "2024-01-10", "2024-01-11", "2024-01-30"])})
    src = pd.DataFrame({"available": pd.to_datetime(["2024-01-01", "2024-01-10", "2024-01-12"]), "v": [1.0, 2.0, 3.0]})
    out = FT.asof(dates, src, ["v"], cap_days=7)
    assert list(out.v[:3]) == [1.0, 2.0, 2.0]          # 01-11 must not see the value published 01-12
    assert np.isnan(out.v[3])                           # 18 days old > 7-day cap: left empty, not carried
def test_asof_changing_the_future_changes_nothing_before_it():
    dates = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=40)})
    rng = np.random.default_rng(0); src = pd.DataFrame({"available": pd.date_range("2023-12-20", periods=60), "v": rng.normal(size=60)})
    a = FT.asof(dates, src, ["v"], 7); cut = ts("2024-01-20")
    src2 = src.copy(); src2.loc[src2.available > cut, "v"] += 100
    b = FT.asof(dates, src2, ["v"], 7)
    assert a.v[dates.Date <= cut].equals(b.v[dates.Date <= cut]) and not a.v[dates.Date > cut].equals(b.v[dates.Date > cut])
def test_weather_is_lagged_five_days():
    days = pd.date_range("2024-01-01", periods=60)
    w = pd.DataFrame({"location_id": 0, "time": days, "precipitation_sum": 1.0, "temperature_2m_max": np.arange(60.0), "temperature_2m_mean": 20.0,
                      "soil_moisture_0_to_7cm_mean": 0.3})
    w12 = w.assign(location_id=12)
    c = FT.weather_candidates(pd.concat([w, w12]), lag_days=5)
    row = c[c.available == ts("2024-02-10")].iloc[0]                         # usable on 10 Feb = window ending 5 Feb
    last_day = (ts("2024-02-05") - ts("2024-01-01")).days
    assert np.isclose(row.wx_bd_tmax_7d, np.mean(np.arange(last_day - 6, last_day + 1))) and np.isclose(row.wx_bd_rain_7d, 7.0)
def test_calendar():
    dates = pd.DataFrame({"Date": pd.to_datetime(["2024-03-10", "2024-03-12", "2024-04-11", "2024-06-10"])})
    re_ = pd.DataFrame({"ramadan_start": ["2024-03-12", "2025-03-02"], "eid_ul_fitr": ["2024-04-11", "2025-03-31"], "eid_ul_adha": ["2024-06-17", "2025-06-07"]})
    cal = FT.calendar(dates, re_, pd.to_datetime(["2024-03-17", "2024-03-26", "2024-04-11"]))
    assert list(cal.days_to_ramadan) == [2, 0, 325, 265] and list(cal.in_ramadan) == [False, True, False, False]
    assert list(cal.days_to_eid_adha) == [99, 97, 67, 7] and list(cal.holiday_next7) == [1, 1, 0, 0]
    assert np.isnan(cal.days_since_prev_report[0]) and list(cal.days_since_prev_report[1:]) == [2, 30, 60]
def frames():
    days = pd.date_range("2024-01-01", "2024-03-31")
    panel = pd.DataFrame([dict(Date=d, item_id=i, Product=i, eval_stratum=s, short_history=False, Price_Avg=50.0 + k, gap_2022=False, report_idx=n)
                          for n, d in enumerate(days[40:]) for k, (i, s) in enumerate([("Onion", "volatile_perishable"), ("Sugar", "imported_staple"), ("Egg", "domestic_staple")])])
    panel.loc[(panel.item_id == "Egg") & (panel.report_idx == 3), "Price_Avg"] = np.nan
    w = pd.concat([pd.DataFrame({"location_id": loc, "time": days[:70], "precipitation_sum": 2.0, "temperature_2m_max": 30.0, "temperature_2m_mean": 25.0,
                                 "soil_moisture_0_to_7cm_mean": 0.3}) for loc in (0, 12)])
    fx = pd.DataFrame({"date": days[:75], "bdt_per_usd": np.linspace(110, 120, 75)})
    ex = pd.DataFrame({"item": ["onion", "rice"], "start": ["2024-02-20", "2024-01-01"], "end": ["2024-03-05", "2024-03-20"]})
    re_ = pd.DataFrame({"ramadan_start": ["2024-03-12"], "eid_ul_fitr": ["2024-04-11"], "eid_ul_adha": ["2024-06-17"]})
    return panel, re_, pd.to_datetime(["2024-03-26"]), w, fx, ex
def build():
    panel, re_, hol, w, fx, ex = frames()
    return panel, FT.build(panel, re_, hol, w, fx, ex, weather_cols=["wx_bd_tmax_7d", "wx_bd_tmean_30d", "wx_bd_rain_7d"], weather_items=["Onion"], weather_lag_days=5,
                           export_items={"onion": ["Onion"]}, fx_strata=["imported_staple"], cap_days=7)
def test_build_unmapped_items_are_empty_not_zero_and_prices_untouched():
    panel, F = build()
    assert len(F) == len(panel) and not F.duplicated(["Date", "item_id"]).any()
    assert F.loc[F.has_weather == 0, ["weather_1", "weather_2", "weather_3"]].isna().all().all()
    assert F.loc[F.has_fx == 0, ["fx_lvl", "fx_ch30"]].isna().all().all() and F.loc[F.has_export_measure == 0, "own_export_measure"].isna().all()
    m = F.merge(panel[["Date", "item_id", "Price_Avg"]], on=["Date", "item_id"], suffixes=("", "_p"))
    assert (m.Price_Avg.isna() == m.Price_Avg_p.isna()).all() and np.allclose(m.Price_Avg.fillna(-1), m.Price_Avg_p.fillna(-1))
    assert F.Price_Avg.isna().sum() == 1 and F.log_price.isna().sum() == 1            # not reported stays empty
def test_build_stale_drivers_go_empty_and_export_flag_follows_dates():
    _, F = build()
    on = F[F.item_id == "Onion"].set_index("Date"); su = F[F.item_id == "Sugar"].set_index("Date")
    assert on.loc["2024-03-10", "weather_3"] == 14.0                                   # 7 days x 2 mm, window ending 5 Mar
    assert pd.notna(on.loc["2024-03-21", "weather_1"]) and pd.isna(on.loc["2024-03-23", "weather_1"])   # weather ends 10 Mar: usable to 15 Mar, carried 7 d
    assert pd.notna(su.loc["2024-03-22", "fx_lvl"]) and pd.isna(su.loc["2024-03-23", "fx_lvl"])         # fx ends 15 Mar, carried 7 d
    assert np.isclose(su.loc["2024-03-01", "fx_lvl"], np.log(np.linspace(110, 120, 75)[60]))            # value of the same day, not a later one
    assert on.loc["2024-02-19", "own_export_measure"] == 0 and on.loc["2024-02-20", "own_export_measure"] == 1 and on.loc["2024-03-06", "own_export_measure"] == 0
    assert pd.isna(on.loc["2024-03-21", "own_export_measure"])                         # after the table's coverage: unknown, not 0

# ---------- part 2: the real table
real = pytest.mark.skipif(not OUT.exists(), reason="S23 not run here")
@pytest.fixture(scope="module")
def F(): return pd.read_parquet(OUT)
@real
def test_rows_keys_no_inf(F):
    p = pd.read_parquet(R / "data/processed" / PC["panel_file"])
    assert len(F) == len(p) and not F.duplicated(["Date", "item_id"]).any()
    assert np.isfinite(F.select_dtypes("number").fillna(0)).all().all()
    a = p.sort_values(["item_id", "Date"]).Price_Avg.fillna(-1).values; b = F.sort_values(["item_id", "Date"]).Price_Avg.fillna(-1).values
    assert np.allclose(a, b), "prices changed"
@real
def test_only_kept_drivers(F):
    banned = ["own_world_price", "own_brent", "own_fishing_ban", "e2_diesel", "e3_", "e4_", "e5_", "fao_"]
    assert not [c for c in F.columns if any(c.startswith(b) for b in banned)]
    assert F.loc[F.has_weather == 0, "weather_1"].isna().all() and F.loc[F.has_fx == 0, "fx_lvl"].isna().all() and F.loc[F.has_export_measure == 0, "own_export_measure"].isna().all()
    assert F.loc[F.has_export_measure == 1].item_id.nunique() == 2
@real
def test_weather_lag_rederived(F):
    from fpw import drivers as D
    w = D.weather(); bd = w[w.location_id <= 10].groupby("time").agg(tmax=("temperature_2m_max", "mean"), tmean=("temperature_2m_mean", "mean"), rain=("precipitation_sum", "mean")).asfreq("D")
    ref = {"wx_bd_tmax_7d": bd.tmax.rolling(7).mean(), "wx_bd_tmean_30d": bd.tmean.rolling(30).mean(), "wx_bd_rain_7d": bd.rain.rolling(7).sum(), "wx_bd_rain_30d": bd.rain.rolling(30).sum()}
    lag = pd.Timedelta(days=fc["weather_lag_days"]); last = w.time.max()
    for i, name in enumerate(fc["weather"], 1):
        if name not in ref: continue
        x = F[F[f"weather_{i}"].notna()]; x = x.sample(min(300, len(x)), random_state=i)
        for r in x.itertuples():
            src_day = min(r.Date - lag, last)                                          # never a day later than report day - 5
            assert np.isclose(ref[name].loc[src_day], getattr(r, f"weather_{i}")), (name, r.Date)
        assert (x.Date - lag - pd.Timedelta(days=fc["carry_cap_days"]) <= last).all()
@real
def test_fx_asof_rederived(F):
    from fpw import drivers as D
    fx = D.fx().sort_values("date"); x = F[F.fx_lvl.notna()].sample(300, random_state=3)
    for r in x.itertuples():
        ok = fx[fx.date <= r.Date].iloc[-1]
        assert np.isclose(np.log(ok.bdt_per_usd), r.fx_lvl) and (r.Date - ok.date).days <= fc["carry_cap_days"]
@real
def test_equals_earlier_feature_table_where_it_exists(F):
    v1 = R / "data/processed/features.parquet"
    if not v1.exists(): pytest.skip("earlier feature table not on this machine")
    a = pd.read_parquet(v1).sort_values(["item_id", "Date"]).reset_index(drop=True)
    b = F[F.Date <= PC["base_last_date"]].sort_values(["item_id", "Date"]).reset_index(drop=True)
    assert len(a) == len(b) and (a.item_id.values == b.item_id.values).all()
    pairs = [(c, c) for c in FT.CAL + ["weather_1", "weather_2", "weather_3", "has_weather", "own_export_measure", "has_export_measure", "log_price"]] + [("e1_fx", "fx_lvl"), ("e1_fx_ch30", "fx_ch30")]
    for old, new in pairs:
        x, y = a[old].astype(float), b[new].astype(float)
        assert ((x.isna() & y.isna()) | np.isclose(x.fillna(0), y.fillna(0))).all() and (x.isna() == y.isna()).all(), (old, new)
