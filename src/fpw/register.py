"""Results register: every number reported for the prediction system is listed in reports/project/RESULTS_REGISTER.md
with the file it comes from, the command that produced it and the code commit. A stage replaces its own section, so reruns do not duplicate."""
import re, subprocess, time
from pathlib import Path
from .paths import ROOT, CODE_ROOT

REGISTER = ROOT / "reports/project/RESULTS_REGISTER.md"


def commit():
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=CODE_ROOT).stdout.strip() or "unknown"


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1000 else f"{v:,.1f}"
    return str(v)


def section(key, title, command, files, rows):
    """rows: list of (measure, value) or (measure, value, file). Replaces the section marked <!-- key --> or appends it."""
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTER.exists():
        REGISTER.write_text((CODE_ROOT / "reports/project/RESULTS_REGISTER.md").read_text(encoding="utf-8"), encoding="utf-8")
    text = REGISTER.read_text(encoding="utf-8")
    head = f"<!-- {key} -->"
    body = [head, f"## {title}", "", f"Run {time.strftime('%Y-%m-%d')}, code commit `{commit()}`.", "", f"Command: `{command}`", "",
            "File(s): " + ", ".join(f"`{f}`" for f in files), "", "| measure | value | file |", "|---|---|---|"]
    for r in rows:
        measure, value = r[0], r[1]; f = r[2] if len(r) > 2 else files[0]
        body.append(f"| {measure} | {_fmt(value)} | `{f}` |")
    body += ["", f"<!-- /{key} -->", ""]
    block = "\n".join(body)
    pat = re.compile(rf"<!-- {re.escape(key)} -->.*?<!-- /{re.escape(key)} -->\n?", re.S)
    text = pat.sub(block, text) if pat.search(text) else text.rstrip() + "\n\n" + block
    REGISTER.write_text(text, encoding="utf-8")
