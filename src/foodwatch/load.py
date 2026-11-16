"""Readers for the four raw files. They only read and rename; they never change a value."""
from io import StringIO

import pandas as pd

from .paths import SETTINGS, raw


def item_ids():
    return [i["id"] for i in SETTINGS["items"]]


def prices():
    """All TCB rows (every item), with item_id = 'Product | Unit'."""
    d = pd.read_csv(raw("prices"), parse_dates=["Date"])
    d["item_id"] = d["Product"] + " | " + d["Unit"]
    return d


def ramadan_eid():
    return pd.read_csv(raw("ramadan_eid"), encoding="utf-8-sig")


def fx():
    """Daily taka per US dollar (Yahoo BDT=X). `available` = the rate's own date (used as of the report date)."""
    d = pd.read_csv(raw("fx"), parse_dates=["Date"]).rename(columns={"Date": "date"})
    d = d.dropna(subset=["bdt_per_usd"]).sort_values("date").reset_index(drop=True)
    d["available"] = d["date"]
    return d[["date", "bdt_per_usd", "available"]]


def weather():
    """Open-Meteo daily rows for 13 locations. The file starts with a location table; the daily table follows it.
    The last day is dropped because it may be incomplete."""
    lines = raw("weather").read_text(encoding="utf-8").splitlines()
    start = [i for i, line in enumerate(lines) if line.startswith("location_id,time")][0]
    w = pd.read_csv(StringIO("\n".join(lines[start:])), parse_dates=["time"])
    w = w[w.time < w.time.max()]
    w.columns = [c.split(" (")[0] for c in w.columns]
    return w
