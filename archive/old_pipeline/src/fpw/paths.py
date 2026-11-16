"""Single source of truth for project paths (light: standard library only).

CODE_ROOT is the git checkout (code, config, tests). ROOT is where data and outputs live: the Google Drive
folder on Colab (set FPW_ARTIFACT_ROOT), the checkout itself on the work PC. Every module takes both from here.
"""
from pathlib import Path
import os

CODE_ROOT = Path(__file__).resolve().parents[2]
if 'FPW_ARTIFACT_ROOT' not in os.environ and Path('/content/drive').is_dir():
    raise RuntimeError('On Colab set FPW_ARTIFACT_ROOT to the Drive project folder before importing fpw.')
ROOT = Path(os.environ.get('FPW_ARTIFACT_ROOT', str(CODE_ROOT))).resolve()
CONFIG_YAML = CODE_ROOT / "config.yaml"
RAW = ROOT / "data/raw/project"          # read-only, hashed by S00
RAW_EXTERNAL = ROOT / "data/raw/external"
PROC = ROOT / "data/processed"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"
STATE = ROOT / "state"
LEDGER = STATE / "stages.json"
