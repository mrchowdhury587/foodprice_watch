"""Single source of truth for project paths (light: standard library only).

Every module and script takes ROOT from here instead of recomputing it.
"""
from pathlib import Path
import os

CODE_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('FPW_ARTIFACT_ROOT', str(CODE_ROOT))).resolve()
CONFIG_YAML = CODE_ROOT / "config.yaml"
RAW = ROOT / "data/raw/project"          # read-only, hashed by S00
RAW_EXTERNAL = ROOT / "data/raw/external"
PROC = ROOT / "data/processed"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"
STATE = ROOT / "state"
LEDGER = STATE / "stages.json"
