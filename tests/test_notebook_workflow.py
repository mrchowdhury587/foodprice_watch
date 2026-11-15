"""Notebook boundaries and failure guards must remain explicit."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[1] / 'notebooks'


def sources(name):
    return [c['source'] for c in json.loads((DIRECTORY / name).read_text())['cells'] if c['cell_type'] == 'code']


def test_planning_notebooks_have_no_side_effects():
    for path in DIRECTORY.glob('0[2-5]_*.ipynb'):
        assert not sources(path.name)


def test_failed_startup_blocks_stage_even_if_old_stage_passed():
    cells = sources('01_data_features.ipynb')
    startup = next(s for s in cells if s.startswith('CHECKS_PASS = False\nstage_ok.clear()'))
    stage = next(s for s in cells if s.startswith('assert CHECKS_PASS') and 'S22' in s)
    namespace = dict(CHECKS_PASS=True, stage_ok={'S22': True}, get_ipython=lambda: SimpleNamespace(user_ns={'_exit_code': 1}))
    # Replace shell execution with a failed shell result; exercise actual guard code.
    with pytest.raises(AssertionError, match='Startup check failed'):
        exec('\n'.join(line for line in startup.splitlines() if not line.startswith('!')), namespace)
    assert not namespace['stage_ok']
    with pytest.raises(AssertionError, match='startup checks'):
        exec('\n'.join(line for line in stage.splitlines() if not line.startswith('!')), namespace)


def test_failed_stage_does_not_leave_success_flag():
    stage = next(s for s in sources('01_data_features.ipynb') if s.startswith('assert CHECKS_PASS') and 'S00' in s)
    namespace = dict(CHECKS_PASS=True, stage_ok={'S00': True}, get_ipython=lambda: SimpleNamespace(user_ns={'_exit_code': 1}))
    with pytest.raises(AssertionError, match='Stage failed'):
        exec('\n'.join(line for line in stage.splitlines() if not line.startswith('!')), namespace)
    assert namespace['stage_ok']['S00'] is False
