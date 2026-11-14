"""Shared loaders (data rules 1-12). Raw files are read-only."""
import pandas as pd, yaml
from .paths import ROOT, RAW, PROC, CONFIG_YAML
CFG = yaml.safe_load(CONFIG_YAML.read_text())
def raw(name): return RAW / name
def panel(version=1):
    """version=1: the earlier panel (stages S01-S11, unchanged). version=2: the extended panel of stage S22 (config/project.yaml panel_file)."""
    import numpy as np
    if version == 1: path = PROC / "tcb_v1.0_rebuilt.parquet"
    else:
        from .project import panel_path; path = panel_path()
    p = pd.read_parquet(path); p["log_price"] = np.log(p.Price_Avg); return p
def item_meta():
    m = pd.read_csv(raw("item_meta.csv"))
    for c in ["first_date","last_date"]:
        s = m[c].astype(str); iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$")      # rule 8: DD-MM-YY (original) or ISO (artifact copy); never guessed
        m[c] = pd.to_datetime(s.where(iso), format="%Y-%m-%d", errors="coerce").fillna(pd.to_datetime(s.where(~iso), format="%d-%m-%y", errors="coerce"))
        assert m[c].notna().all(), f"unparseable item_meta {c}"
    m["short_history"] = m["short_history"].astype(str).str.upper().eq("TRUE")
    return m
