"""The registry (code) and the ledger (state/stages.json) must agree; scripts and tests it names must exist."""
import json, re
from pathlib import Path
from fpw.registry import STAGES
from fpw import runner

R = Path(__file__).resolve().parents[1]
LEDGER = {s["id"]: s for s in json.loads((R / "state/stages.json").read_text())["stages"]}


def test_registry_ids_are_in_ledger():
    assert set(STAGES) <= set(LEDGER)


def test_ledger_outputs_are_produced_by_registry_stage():
    for sid, spec in STAGES.items():
        assert set(LEDGER[sid]["outputs"]) <= set(spec["outputs"]), sid


def test_named_scripts_and_tests_exist():
    for sid, spec in STAGES.items():
        cmds = spec["run"]
        for c in cmds:
            m = re.search(r"(src/stages/\S+\.py)", c)
            assert m and (R / m.group(1)).exists(), (sid, c)
        for t in spec["tests"]:
            assert (R / t).exists(), (sid, t)


def test_notes_are_safe_on_a_shell_command_line():
    """runner.py and the notebook pass the note unquoted to `finalize.py SNN <note>`; a ; | & < > ( ) or quote would split or break that command."""
    for sid, spec in STAGES.items():
        assert not set(spec.get("note", "")) & set(";|&<>()$`'\"\\"), (sid, spec.get("note"))
    assert runner.plan("S22")[-1].startswith("python src/stages/finalize.py S22 ")
