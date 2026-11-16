"""Where things live. Code and settings come from the repo; data and outputs live under DATA_ROOT (Drive in Colab), never in git."""
import hashlib, os
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SETTINGS = yaml.safe_load((REPO / "config/settings.yaml").read_text(encoding="utf-8"))
DATA_ROOT = Path(os.environ.get("FW_DATA_ROOT", SETTINGS["drive"]["data_root"]))
RAW = DATA_ROOT / "raw"


def data(key):
    """Path of an output named in settings `files` (e.g. data("panel"))."""
    return DATA_ROOT / SETTINGS["files"][key]


def raw(key):
    """Path of a raw input named in settings `raw_files` (e.g. raw("prices"))."""
    return RAW / SETTINGS["raw_files"][key]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(df, path):
    """Atomic write: a half-written file never replaces a good one.
    LF line ends and 10 significant digits so the same data gives the same sha256 on Windows and in Colab."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, lineterminator="\n", float_format="%.10g")
    tmp.replace(path)
    return sha256(path)
