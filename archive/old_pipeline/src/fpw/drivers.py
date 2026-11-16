"""Driver loaders used by the prediction system: exchange rate, weather, events. (IMF, FAO, Brent, Comtrade loaders: see archive/earlier_design.)"""
import numpy as np, pandas as pd
from .io import raw, CFG
def fx():
    y = pd.read_csv(raw("yahoo_bdt_per_usd.csv"), parse_dates=["Date"]).rename(columns={"Date": "date", "bdt_per_usd": "yahoo"})
    n = pd.read_csv(raw("usd_cross_rates_npm_2024_2026.csv"), parse_dates=["date"])[["date", "bdt_per_usd"]].rename(columns={"bdt_per_usd": "npm"})
    d = y.merge(n, on="date", how="outer").sort_values("date")
    cut = pd.Timestamp(CFG["fx_splice"]["npm_from"])
    d["bdt_per_usd"] = np.where(d.date >= cut, d.npm, d.yahoo * CFG["fx_splice"]["yahoo_scale"])
    d = d.dropna(subset=["bdt_per_usd"]); d["available"] = d.date
    return d
def weather():
    lines = raw("weather_open_meteo_13_locations_2019_2026.csv").read_text(encoding="utf-8").splitlines()
    k = [i for i, l in enumerate(lines) if l.startswith("location_id,time")][0]
    from io import StringIO
    w = pd.read_csv(StringIO("\n".join(lines[k:])), parse_dates=["time"])
    w = w[w.time < w.time.max()]                                            # rule 16: drop incomplete last day
    w.columns = [c.split(" (")[0] for c in w.columns]
    return w
def events(name):
    return pd.read_csv(raw(name), encoding="utf-8-sig")                     # rule 19
