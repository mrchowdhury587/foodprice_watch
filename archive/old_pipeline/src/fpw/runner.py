"""Run one stage the way the Colab notebook does: `python -m fpw.runner S22 [--dry]` (or `make stage S=S22`).

Skips done/blocked/skipped stages, refuses to start before its dependencies are done, runs each command,
then finalizes (acceptance tests -> ledger -> PROGRESS.md). Never commits: commits come from the work PC.
Standard library only.
"""
import subprocess, sys
from .paths import CODE_ROOT
from .registry import STAGES
from . import state


def sh(cmd: str) -> int:
    print(f"\n$ {cmd}", flush=True)
    return subprocess.run(cmd, shell=True, cwd=CODE_ROOT).returncode


def plan(sid: str):
    """The commands this stage would run now (used by --dry and by run)."""
    spec = STAGES[sid]
    return list(spec["run"]) + [f"python src/stages/finalize.py {sid} {spec.get('note', '')}".strip()]


def run(sid: str, dry: bool = False) -> int:
    if sid not in STAGES:
        print(f"{sid}: not a runnable stage here (earlier-design stages are in archive/; S24-S33 are not implemented yet)")
        return 2
    led = {s["id"]: s for s in state.load()["stages"]}
    st = led[sid]["status"]
    if st in ("done", "skipped"):
        print(f"{sid} already {st} - nothing to do"); return 0
    if st == "blocked":
        print(f"{sid} is blocked: {led[sid]['notes']}"); return 1
    waiting = [d for d in led[sid]["depends_on"] if led[d]["status"] not in ("done", "skipped")]
    if waiting:
        print(f"{sid} depends on {waiting}, which are not done"); return 1
    for cmd in plan(sid):
        if dry:
            print("DRY:", cmd); continue
        if sh(cmd) != 0:
            print(f"STOP: {sid} failed at: {cmd}"); return 1
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit("usage: python -m fpw.runner S22 [--dry]")
    sys.exit(run(args[0].upper() if args[0][0].lower() == "s" else f"S{int(args[0]):02d}", dry="--dry" in sys.argv))
