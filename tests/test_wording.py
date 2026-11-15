from pathlib import Path
import yaml
from fpw.paths import ROOT as R, CODE_ROOT
def test_no_banned_words_in_reports():
    banned = yaml.safe_load((CODE_ROOT/"config.yaml").read_text())["banned_words"]
    for p in list((R/"reports").rglob("*.csv")) + list((R/"reports").rglob("*.md")):
        if p.name == "REVIEW.md": continue
        t = p.read_text(errors="ignore").lower()
        for w in banned: assert w not in t, f"{w} in {p}"
