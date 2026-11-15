"""Exercise code updates against small local Git repositories, without prices."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('colab_sync', Path(__file__).resolve().parents[1] / 'tools/colab_sync.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'user.name=Test', '-c',
                                    'user.email=test@example.com', *args], cwd=root, text=True).strip()


def commit(root, message):
    git(root, 'add', '-A')
    git(root, 'commit', '-qm', message)


def repositories(tmp_path):
    upstream, drive = tmp_path / 'upstream', tmp_path / 'drive'
    upstream.mkdir()
    git(upstream, 'init', '-b', 'main')
    (upstream / 'state').mkdir()
    (upstream / 'state/stages.json').write_text(json.dumps({'stages': [dict(id='S00', title='Intake', status='pending')]}))
    (upstream / 'code.txt').write_text('initial\n')
    commit(upstream, 'initial')
    git(tmp_path, 'clone', str(upstream), str(drive))
    return upstream, drive


def test_diverged_history_preserves_drive_status_and_updates_code(tmp_path):
    upstream, drive = repositories(tmp_path)
    ledger = drive / 'state/stages.json'
    ledger.write_text(json.dumps({'stages': [dict(id='S00', title='Intake', status='done', output_sha256={'example': 'hash'})]}))
    commit(drive, 'runtime finalized intake')
    original = git(drive, 'rev-parse', 'HEAD')
    (upstream / 'state/stages.json').write_text(json.dumps({'stages': [dict(id='S00', title='Intake', status='pending', notes='GitHub note')]}))
    (upstream / 'code.txt').write_text('updated\n')
    commit(upstream, 'updated code and local ledger')
    module.sync(drive)
    assert (drive / 'code.txt').read_text() == 'updated\n'
    assert json.loads(ledger.read_text())['stages'][0]['status'] == 'done'
    assert json.loads(ledger.read_text())['stages'][0]['output_sha256'] == {'example': 'hash'}
    git(drive, 'merge-base', '--is-ancestor', original, 'HEAD')
    assert not git(drive, 'status', '--porcelain')
    # Reconnect/update with no new remote commits remains a clean no-op.
    module.sync(drive)
    assert not git(drive, 'status', '--porcelain')


def test_unexpected_code_conflict_aborts_and_preserves_original(tmp_path):
    upstream, drive = repositories(tmp_path)
    (drive / 'code.txt').write_text('local edit\n')
    commit(drive, 'local change')
    original = git(drive, 'rev-parse', 'HEAD')
    (upstream / 'code.txt').write_text('upstream edit\n')
    commit(upstream, 'upstream change')
    with pytest.raises(RuntimeError, match='merge undone'):
        module.sync(drive)
    assert git(drive, 'rev-parse', 'HEAD') == original
    assert (drive / 'code.txt').read_text() == 'local edit\n'
    assert not git(drive, 'status', '--porcelain')
