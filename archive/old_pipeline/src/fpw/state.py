"""Ledger helpers: update only status fields of state/stages.json (atomic)."""
import json, os, time
from .checkpoint import sha256
from .paths import ROOT, LEDGER, CODE_ROOT
ALLOWED = {"status","started_at","last_unit","units_done","output_sha256","git_commit","finished_at","notes"}
def load():
    """The ledger in ROOT (Drive in Colab). Stages appended to the repo ledger later (new entries only, never edits) are added when missing."""
    d = json.loads(LEDGER.read_text()); repo = CODE_ROOT / "state/stages.json"
    if repo.exists() and repo.resolve() != LEDGER.resolve():
        have = {s["id"] for s in d["stages"]}
        d["stages"] += [s for s in json.loads(repo.read_text())["stages"] if s["id"] not in have]
    return d
def save(d):
    tmp = LEDGER.with_suffix(".tmp"); tmp.write_text(json.dumps(d, indent=2)); os.replace(tmp, LEDGER)
def stage(d, sid): return next(s for s in d["stages"] if s["id"] == sid)
def update(sid, **kw):
    assert set(kw) <= ALLOWED, set(kw) - ALLOWED
    d = load(); s = stage(d, sid); s.update(kw); save(d)
def start(sid):
    d = load(); s = stage(d, sid)
    if s["status"] != "in_progress":
        s["status"] = "in_progress"; s["started_at"] = s["started_at"] or time.strftime("%Y-%m-%dT%H:%M:%S")
    save(d)
def finish(sid, outputs, notes=None, status="done"):
    d = load(); s = stage(d, sid)
    s["output_sha256"] = {o: sha256(ROOT / o) for o in outputs}
    s["status"] = status; s["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    if notes is not None: s["notes"] = notes
    save(d)
