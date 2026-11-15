import csv, json
from pathlib import Path
import pytest, yaml
from fpw.paths import ROOT as R, CODE_ROOT
OLD = ["S00", "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12", "S13", "S14", "S99"]
NEW = [f"S{n}" for n in range(22, 34)]          # prediction-system track, appended 2026-11-15
@pytest.mark.skipif(not (R/"data/raw/MANIFEST.csv").exists(), reason="S00 not run here (data lives on Drive; finalize.py refuses a missing MANIFEST)")
def test_manifest_present():
    rows = list(csv.DictReader((R/"data/raw/MANIFEST.csv").open()))
    assert sum(r["status"]=="present" and r["path"].startswith("data/raw/project/") for r in rows) >= 32   # 32 original files + optional extra_raw_files
def test_ledger_valid():
    ids = [s["id"] for s in json.loads((R/"state/stages.json").read_text())["stages"]]
    assert ids[:16] == OLD, "old entries deleted or reordered"
    assert ids[16:] == NEW, "new stages must be appended in order"
def test_project_settings_match_frozen_config():
    c = yaml.safe_load((CODE_ROOT/"config/project.yaml").read_text(encoding="utf-8")); old = yaml.safe_load((CODE_ROOT/"config.yaml").read_text(encoding="utf-8"))
    assert c["horizons"] == old["horizons"] and c["test"]["period"] == old["split"]["test"]
    assert len(range(c["test"]["first_cutoff"], c["test"]["last_cutoff"] + 1, c["test"]["step"])) == 87
    assert c["alerts"]["event_window_days"] == old["alerts"]["event_window_days"] and c["alerts"]["persistence"] == old["alerts"]["persistence"]
