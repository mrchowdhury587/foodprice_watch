"""Build the prediction-track handover notebook without runtime outputs."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cells = []


def add(kind, source):
    cell = dict(cell_type=kind, metadata={}, source=source.strip() + '\n')
    if kind == 'code':
        ast.parse(cell['source'])
        cell.update(execution_count=None, outputs=[])
    cells.append(cell)


add('markdown', '''# Bangladesh Food Price Watch — prediction system resume
Source: the repository notebook and the 2026-11-15 handover. The private Drive notebook was not accessible; its saved outputs are not copied here.

Push this notebook **and the merged source code** to GitHub before opening it in Colab.
Use the Google account holding `MyDrive/FoodPriceWatch` (handover: mehedi11908015@gmail.com).
Choose a GPU runtime if desired; the current scripts use their existing CPU settings.

Run setup, then **one stage cell at a time**. Paste its full output back to the agent and stop for review.
Do not use Run all. This notebook does not run the earlier benchmark or sealed tests.

Remaining: verify S00/S22/S23 on Drive; implement S24 stacked model; confirm S25 candidates and validation period; selection S25; tuning S26; committed pre-registration and one sealed test S27; ranges/alerts S28; explanations S29; production fit/exports S30; dashboard S31; update script S32; docs S33. Report writing follows verified results.
''')
add('markdown', '## 1. Mount Drive\nAuthorize the account containing the existing project data. No temporary-storage fallback is used.')
add('code', '''from google.colab import drive
from pathlib import Path
import os, sys, subprocess, json, hashlib, csv
drive.mount('/content/drive')
ROOT = Path('/content/drive/MyDrive/FoodPriceWatch')
assert Path('/content/drive/MyDrive').is_dir(), 'STOP: Drive is not mounted'
print('Project root:', ROOT)
print('Existing project folder:', ROOT.exists())
''')
add('markdown', '## 2. Load code\nUpdates preserve Drive stage status and local stage commits, including when histories diverge. A backup branch is created before merging. Unexpected conflicts stop the update and undo the merge. Uncommitted changes need agent review.')
sync_source = (ROOT / 'tools/colab_sync.py').read_text(encoding='utf-8').split("if __name__ == '__main__':")[0]
add('code', sync_source + '''
REPO = 'https://github.com/mrchowdhury587/foodprice_watch.git'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
if not (ROOT / '.git').exists():
    assert not ROOT.exists() or not any(ROOT.iterdir()), 'STOP: existing non-Git folder; ask the agent to attach code without replacing data'
    ROOT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', REPO, str(ROOT)], check=True)
else:
    sync(ROOT)
for name in ['src/fpw/features.py', 'src/stages/s23_features.py']:
    assert (ROOT / name).is_file(), 'STOP: push merged feature code to GitHub first: ' + name
subprocess.run(['git', 'config', 'user.name', 'FPW runner'], cwd=ROOT, check=True)
subprocess.run(['git', 'config', 'user.email', 'fpw@example.com'], cwd=ROOT, check=True)
os.chdir(ROOT)
os.environ['PYTHONPATH'] = str(ROOT / 'src')
sys.path.insert(0, str(ROOT / 'src'))
print('Code commit:', git('rev-parse', 'HEAD'))
''')
add('markdown', '## 3. Install runtime packages')
add('code', '''subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements-colab.txt')], check=True)
os.environ.setdefault('FPW_THREADS', str(os.cpu_count() or 2))
print('Package install: PASS; threads:', os.environ['FPW_THREADS'])
''')
add('markdown', '## 4. Startup verification\nA failed check stops execution. Missing or changed finished outputs are reset to pending by the project checker; paste failures back before continuing.')
add('code', '''for folder in ['outputs', 'data']:
    for tmp in (ROOT / folder).rglob('*.tmp'):
        assert tmp.resolve().is_relative_to(ROOT.resolve())
        tmp.unlink()
        print('Removed interrupted-write temporary file:', tmp.relative_to(ROOT))
subprocess.run([sys.executable, '-m', 'fpw.check'], cwd=ROOT, check=True)
def run_unit(sid):
    subprocess.run([sys.executable, '-m', 'fpw.runner', sid], cwd=ROOT, check=True)
    ledger = json.loads((ROOT / 'state/stages.json').read_text())
    stage = next(s for s in ledger['stages'] if s['id'] == sid)
    assert stage['status'] == 'done', 'STOP: stage was not finalized'
    summary = []
    for name, expected in stage['output_sha256'].items():
        path = ROOT / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, 'STOP: output hash mismatch: ' + name
        rows = None
        if path.suffix == '.csv':
            with path.open(newline='') as f:
                rows = sum(1 for _ in csv.DictReader(f))
        elif path.suffix == '.parquet':
            import pyarrow.parquet as pq
            rows = pq.read_metadata(path).num_rows
        summary.append(dict(file=name, rows=rows, sha256=actual))
    assert summary, 'STOP: no finalized output hashes'
    print(json.dumps(dict(unit=sid, outputs=summary, check='PASS', git_commit=git('rev-parse', 'HEAD')), indent=2))
''')
add('markdown', '''## 5. S00 — refresh intake
Before running, place the extended CSV `tcb_dhaka_daily_prices_2021_2026_v2.csv` in `inbox/project/`.
Existing original project files must be in `data/raw/project/` or `inbox/project/`.
This refreshes the intake manifest and its finalized hashes. Paste the output back and stop.''')
add('code', '''subprocess.run([sys.executable, 'src/stages/s00_intake.py'], cwd=ROOT, check=True)
subprocess.run([sys.executable, 'src/stages/finalize.py', 'S00'], cwd=ROOT, check=True)
run_unit('S00')
''')
add('markdown', '''## 6. S22 — extended panel
Run after S00 output is reviewed. The earlier S01 panel must already exist on Drive for the equality checks. Audit tables from the work-PC audit must be available. Missing prerequisites require agent review; do not rerun the old benchmark.''')
add('code', "run_unit('S22')")
add('markdown', '''## 7. S23 — kept features
Run after S22 output is reviewed. Requires the earlier driver artifacts and feature table for comparison. Paste the output back and stop.''')
add('code', "run_unit('S23')")
add('markdown', '''## 8. Inspect remaining work — no training or testing here
S24–S33 are not implemented by this notebook. Their pending status is not evidence of completed training.
Before S25, confirm candidates/winner rule and validation period (`TO_CONFIRM` in config/project.yaml).
The test must follow committed pre-registration and the existing seal mechanism. Never tune on test results.
Keep data, models and exports out of GitHub.''')
add('code', '''ledger = json.loads((ROOT / 'state/stages.json').read_text())
for stage in ledger['stages']:
    if stage['id'] in {f'S{i}' for i in range(22, 34)}:
        print(stage['id'], stage['status'], '-', stage['title'])
print('Unconfirmed settings:')
for line in (ROOT / 'config/project.yaml').read_text().splitlines():
    if 'TO_CONFIRM' in line and not line.lstrip().startswith('#'):
        print(line)
''')
notebook = dict(cells=cells, metadata=dict(kernelspec=dict(display_name='Python 3', language='python', name='python3'), language_info=dict(name='python'), colab=dict(name='FoodPriceWatch_Prediction_Resume.ipynb')), nbformat=4, nbformat_minor=4)
target = ROOT / 'FoodPriceWatch_Prediction_Resume.ipynb'
target.write_text(json.dumps(notebook, indent=1) + '\n', encoding='utf-8')
print('Notebook built; all code cells parse; outputs empty:', target.name)
# Keep the established GitHub/Colab notebook URL as the primary entry point.
notebook['metadata']['colab']['name'] = 'FoodPriceWatch_Colab.ipynb'
(ROOT / 'FoodPriceWatch_Colab.ipynb').write_text(json.dumps(notebook, indent=1) + '\n', encoding='utf-8')
print('Original notebook updated for the prediction track: FoodPriceWatch_Colab.ipynb')

# Group the existing verified workflow into six manageable entry points.
directory = ROOT / 'notebooks'
directory.mkdir(exist_ok=True)
setup = cells[1:9]
groups = [
    ('00_setup', 'Environment and code setup', setup),
    ('01_data_features', 'Intake, panel, audit and features', setup[:2] + setup[4:] + cells[9:15]),
    ('02_model_training', 'Model implementation, selection and tuning', []),
    ('03_evaluation', 'Sealed testing, ranges, alerts and explanations', []),
    ('04_production', 'Production exports, dashboard and updates', []),
    ('05_results_documentation', 'Results, limitations and documentation', []),
]
stages = {
    '02_model_training': [('S24', 'Stacked-model implementation checks'), ('S25', 'Validation-based model selection'), ('S26', 'Tuning and validation confirmation')],
    '03_evaluation': [('S27', 'Committed pre-registration and sealed test'), ('S28', 'Ranges and alert evaluation'), ('S29', 'Driver explanations')],
    '04_production': [('S30', 'Production training and exports'), ('S31', 'Local dashboard instructions'), ('S32', 'Production update workflow')],
    '05_results_documentation': [('S33', 'Documentation and report readiness')],
}
def markdown(text):
    return dict(cell_type='markdown', metadata={}, source=text + '\n')

links = []
for name, title, body in groups:
    intro = markdown(f'# {name[:2]}. {title}\nRun setup first. Use the same Drive project folder. Run one stage cell at a time and share its output for review. Never use Run all across stages.')
    content = [intro] + body
    if name in stages:
        content += setup[:2] + setup[4:]
        for sid, description in stages[name]:
            content.append(markdown(f'## {sid}: {description}\n**Not implemented yet.** No execution command is provided. Prerequisites and required decisions must be verified before this stage is implemented.'))
        content.append(markdown('Testing requires committed pre-registration and existing checkpoint enforcement. Do not rerun earlier sealed tests. Keep models, exports and data out of GitHub.'))
    if name != '00_setup':
        initialization = """assert (ROOT / 'src/fpw/runner.py').is_file(), 'Run notebook 00 first'
os.chdir(ROOT)
os.environ['PYTHONPATH'] = str(ROOT / 'src')
sys.path.insert(0, str(ROOT / 'src'))
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
"""
        content.insert(3, dict(cell_type='code', metadata={}, source=initialization, execution_count=None, outputs=[]))
    document = dict(notebook, cells=content, metadata=dict(notebook['metadata']))
    document['metadata']['colab'] = dict(name=name + '.ipynb')
    (directory / (name + '.ipynb')).write_text(json.dumps(document, indent=1) + '\n', encoding='utf-8')
    links.append(f'- [{name}.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/{name}.ipynb): {title}')
index = dict(notebook, cells=[markdown('# Food Price Watch notebook index\n\n' + '\n'.join(links) + '\n\nStart with 00. Existing Drive Git conflicts must be resolved before continuing. Training and testing are not completed by this reorganization.')])
for filename in ['FoodPriceWatch_Colab.ipynb', 'FoodPriceWatch_Prediction_Resume.ipynb']:
    (ROOT / filename).write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
(directory / 'README.md').write_text('# Colab workflow\n\n' + '\n'.join(links) + '\n\nAfter reconnecting, initialize the selected notebook again. Only 00 synchronizes Git. All notebooks share Drive state. Stop after each stage and paste output for review. Missing prerequisites or conflicts block execution. Notebooks 02-05 mark unfinished stages explicitly; they do not train or score models. Report writing follows verified, registered results.\n', encoding='utf-8')
print('Six numbered notebooks and compatibility indexes generated.')
