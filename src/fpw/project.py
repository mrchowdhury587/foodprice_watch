"""Settings of the prediction-system track (stages S22-S33): config/project.yaml.

config.yaml stays frozen (the old run's unit markers record its hash), so new settings are read from here.
`need(key)` stops a stage that depends on a setting still marked TO_CONFIRM.
"""
import yaml
from .paths import ROOT, RAW, PROC, CODE_ROOT

PROJECT_YAML = CODE_ROOT / "config/project.yaml"
PCFG = yaml.safe_load(PROJECT_YAML.read_text(encoding="utf-8"))


def need(*keys):
    """PCFG[k1][k2]...; raises if the value is missing or still TO_CONFIRM (an open question for the user)."""
    v = PCFG
    for k in keys:
        if not isinstance(v, dict) or k not in v:
            raise KeyError(f"config/project.yaml: {'.'.join(keys)} is missing")
        v = v[k]
    if v == "TO_CONFIRM":
        raise RuntimeError(f"config/project.yaml: {'.'.join(keys)} is TO_CONFIRM; ask the user before this step")
    return v


def price_csv():
    return RAW / PCFG["price_file"]


def panel_path():
    return PROC / PCFG["panel_file"]


def features_path():
    return PROC / PCFG["features_file"]


def out_dir(kind):
    """kind: tables | figures | exports | models. Created on demand."""
    p = ROOT / PCFG["paths"][kind]
    p.mkdir(parents=True, exist_ok=True)
    return p
