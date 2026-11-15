"""Update a Drive checkout while preserving its committed stage state."""
import json
from pathlib import Path
import subprocess
import time

STATUS_FIELDS = {'status', 'started_at', 'last_unit', 'units_done',
                 'output_sha256', 'git_commit', 'finished_at', 'notes'}


def sync(root):
    root = Path(root)

    def git(*args, check=True):
        result = subprocess.run(['git', *args], cwd=root, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.stdout.strip():
            print(result.stdout.strip())
        if check and result.returncode:
            raise RuntimeError('STOP: git ' + ' '.join(args) + ' failed; see output above')
        return result

    assert not git('status', '--porcelain').stdout.strip(), 'STOP: uncommitted changes; send git status to the agent'
    assert git('branch', '--show-current').stdout.strip() == 'main', 'STOP: expected main branch'
    for name in ['MERGE_HEAD', 'rebase-merge', 'rebase-apply']:
        path = git('rev-parse', '--git-path', name).stdout.strip()
        assert not (root / path).exists(), 'STOP: unfinished Git operation'
    git('fetch', 'origin', 'main')
    # Local runtime status is authoritative; GitHub carries code, not Drive evidence.
    local = json.loads((root / 'state/stages.json').read_text())
    remote = json.loads(git('show', 'origin/main:state/stages.json').stdout)
    by_id = {s['id']: s for s in remote['stages']}
    for stage in local['stages']:
        assert stage['id'] in by_id, 'STOP: upstream removed a stage'
        other = by_id[stage['id']]
        assert {k: v for k, v in stage.items() if k not in STATUS_FIELDS} == {
            k: v for k, v in other.items() if k not in STATUS_FIELDS
        }, 'STOP: stage definition changed; agent review required: ' + stage['id']
        for key in STATUS_FIELDS:
            if key in stage:
                other[key] = stage[key]
    backup = 'backup/colab-before-sync-' + str(time.time_ns())
    git('branch', backup)
    print('Previous committed state preserved at:', backup)
    git('config', 'user.name', 'FPW runner')
    git('config', 'user.email', 'fpw@example.com')
    result = git('merge', '--no-ff', '--no-commit', 'origin/main', check=False)
    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
    if result.returncode and (not conflicts or set(conflicts) - {'state/stages.json'}):
        git('merge', '--abort', check=False)
        raise RuntimeError('STOP: update conflict; merge undone, previous commits retained. Send the output above to the agent')
    ledger = root / 'state/stages.json'
    # Write only when content changed, using an atomic replacement.
    if conflicts or json.loads(ledger.read_text()) != remote:
        temporary = ledger.with_suffix('.sync.tmp')
        temporary.write_text(json.dumps(remote, indent=2) + '\n')
        temporary.replace(ledger)
    git('add', 'state/stages.json')
    merge_head = root / git('rev-parse', '--git-path', 'MERGE_HEAD').stdout.strip()
    if merge_head.exists() or git('diff', '--cached', '--quiet', check=False).returncode:
        git('commit', '-m', 'Sync project code while preserving Drive stage state')
    print('Code update complete. Runtime data and prior commits retained.')
    git('log', '--oneline', '-3')


if __name__ == '__main__':
    import sys
    sync(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
