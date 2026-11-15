"""The stage notebook must keep its failure guards: a failed startup check blocks every stage cell."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / 'notebooks' / 'run_stage.ipynb'


def sources():
    return [''.join(c['source']) for c in json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells'] if c['cell_type'] == 'code']


def run(cell, **namespace):
    # Shell lines (!, %) cannot run here; the guards around them are what we test.
    lines = [l[:len(l) - len(l.lstrip())] + 'pass' if l.lstrip().startswith(('!', '%')) else l for l in cell.splitlines()]
    code = '\n'.join(lines)
    exec(code, namespace)
    return namespace


def test_failed_startup_blocks_stage_even_if_old_stage_passed():
    startup = next(s for s in sources() if s.startswith('CHECKS_PASS = False\nstage_ok.clear()'))
    stage = next(s for s in sources() if s.startswith("STAGE = "))
    ipy = lambda: SimpleNamespace(user_ns={'_exit_code': 1})
    with pytest.raises(AssertionError, match='Startup check failed'):
        run(startup, CHECKS_PASS=True, stage_ok={'S22': True}, get_ipython=ipy)
    with pytest.raises(AssertionError, match='startup checks'):
        run(stage, CHECKS_PASS=False, stage_ok={}, get_ipython=ipy)


def test_failed_stage_does_not_leave_success_flag():
    stage = next(s for s in sources() if s.startswith("STAGE = "))
    ns = dict(CHECKS_PASS=True, stage_ok={'S22': True}, get_ipython=lambda: SimpleNamespace(user_ns={'_exit_code': 1}))
    with pytest.raises(AssertionError, match='Stage failed'):
        run(stage, **ns)
    assert ns['stage_ok']['S22'] is False


def test_setup_points_artifacts_at_drive_and_code_at_clone():
    text = '\n'.join(sources())
    assert 'FPW_ARTIFACT_ROOT=/content/drive/MyDrive/FoodPriceWatch' in text
    assert '/content/foodprice_watch' in text
