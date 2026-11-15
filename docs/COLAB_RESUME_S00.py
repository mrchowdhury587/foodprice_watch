# Run this ONE cell after notebook setup cells 1-4, then paste its output back.
from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess
import sys

root = Path('/content/drive/MyDrive/FoodPriceWatch')
assert Path('/content/drive/MyDrive').is_dir(), 'STOP: mount the intended Google Drive first'
assert (root / '.git').exists(), 'STOP: run notebook setup cells 1-4 first'
assert (root / 'src/fpw/runner.py').is_file(), 'STOP: project code is missing'
env = dict(os.environ, PYTHONPATH=str(root / 'src'))
result = subprocess.run([sys.executable, '-m', 'fpw.runner', 'S00'], cwd=root, env=env)
assert result.returncode == 0, 'STOP: S00 failed; paste the full output'
manifest = root / 'data/raw/MANIFEST.csv'
with manifest.open(newline='') as f:
    rows = list(csv.DictReader(f))
stage = next(s for s in json.loads((root / 'state/stages.json').read_text())['stages'] if s['id'] == 'S00')
valid = stage['status'] == 'done' and bool(stage['output_sha256'])
for name, expected in stage['output_sha256'].items():
    path = root / name
    valid = valid and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected
print(json.dumps(dict(unit='S00', rows=len(rows),
    sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    check='PASS' if valid else 'FAIL',
    missing=[r['path'] for r in rows if r['status'] != 'present'],
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()), indent=2))
assert valid, 'STOP: S00 ledger/output verification failed'
