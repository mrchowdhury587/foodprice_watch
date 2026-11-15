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

# Group the existing verified workflow into five manageable entry points.
directory = ROOT / 'notebooks'
directory.mkdir(exist_ok=True)
setup = cells[1:9]
groups = [
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
    intro = markdown(f'# {name[:2]}. {title}\nStart with notebook 01. Use the same Drive project folder. Run one stage cell at a time and share its output for review. Never use Run all across stages.')
    content = [intro] + body
    if name in stages:
        content += setup[:2] + setup[4:]
        for sid, description in stages[name]:
            content.append(markdown(f'## {sid}: {description}\n**Not implemented yet.** No execution command is provided. Prerequisites and required decisions must be verified before this stage is implemented.'))
        content.append(markdown('Testing requires committed pre-registration and existing checkpoint enforcement. Do not rerun earlier sealed tests. Keep models, exports and data out of GitHub.'))
    # Replace the old mount/setup prefix with two minimal connection cells.
    mount = "from google.colab import drive\ndrive.mount('/content/drive')\n"
    pull = """%%bash
set -e
REPO_DIR='/content/drive/MyDrive/FoodPriceWatch'
REPO_URL='https://github.com/mrchowdhury587/foodprice_watch.git'
if [ ! -d "$REPO_DIR/.git" ]; then
    git clone -b main "$REPO_URL" "$REPO_DIR"
else
    git -C "$REPO_DIR" pull --no-rebase origin main
fi
"""
    initialization = """from pathlib import Path
import os, sys, subprocess, json, hashlib, csv
ROOT = Path('/content/drive/MyDrive/FoodPriceWatch')
assert (ROOT / 'src/fpw/runner.py').is_file(), 'Repository is missing on Drive'
os.chdir(ROOT)
os.environ['PYTHONPATH'] = str(ROOT / 'src')
sys.path.insert(0, str(ROOT / 'src'))
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
"""
    def code(source):
        return dict(cell_type='code', metadata={}, source=source, execution_count=None, outputs=[])
    content = [intro, markdown('## Connect Drive'), code(mount),
               markdown('## Get main from GitHub into temporary Colab storage\nCode is cloned from main into /content/foodprice_watch, or updated there on later runs. Drive is used only for persistent artifacts. The old Drive checkout is not pulled or changed.'), code(pull),
               markdown('## Initialize project runtime\nPersistent artifacts are saved under the Drive project folder.'), code(initialization)] + content[3:]
    # Notebook-facing execution uses Colab magics and Python entry points.
    for cell in content:
        if cell['cell_type'] != 'code':
            continue
        source = cell['source']
        if source.startswith("subprocess.run([sys.executable, '-m', 'pip'"):
            source = "%%bash\nset -e\ncd /content/drive/MyDrive/FoodPriceWatch\npython -m pip install -q -r requirements-colab.txt\n"
        else:
            source = source.replace('import os, sys, subprocess, json, hashlib, csv', 'import os, sys, json, hashlib, csv, runpy')
            source = source.replace("def git(*args):\n    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()", """os.environ.setdefault('FPW_THREADS', str(os.cpu_count() or 2))
def run_python(path, *arguments, module=False):
    previous = sys.argv[:]
    try:
        sys.argv = [path, *arguments]
        if module:
            runpy.run_module(path, run_name='__main__')
        else:
            runpy.run_path(path, run_name='__main__')
    except SystemExit as result:
        if result.code not in (None, 0):
            raise RuntimeError(f'{path} failed: {result.code}') from result
    finally:
        sys.argv = previous
""")
            source = source.replace("subprocess.run([sys.executable, '-m', 'fpw.check'], cwd=ROOT, check=True)", "run_python('fpw.check', module=True)")
            source = source.replace("subprocess.run([sys.executable, '-m', 'fpw.runner', sid], cwd=ROOT, check=True)", "from fpw.runner import run\n    assert run(sid) == 0, 'STOP: stage failed'")
            source = source.replace("git_commit=git('rev-parse', 'HEAD')", "git_commit=stage.get('git_commit')")
            source = source.replace("subprocess.run([sys.executable, 'src/stages/s00_intake.py'], cwd=ROOT, check=True)", "run_python('src/stages/s00_intake.py')")
            source = source.replace("subprocess.run([sys.executable, 'src/stages/finalize.py', 'S00'], cwd=ROOT, check=True)", "run_python('src/stages/finalize.py', 'S00')")
        assert 'subprocess' not in source
        cell['source'] = source
    # Execute scripts in fresh Python processes using visible notebook commands.
    direct = []
    prefix = '%%bash\nset -e\ncd /content/drive/MyDrive/FoodPriceWatch\nexport PYTHONPATH=src\n'
    for cell in content:
        if cell['cell_type'] != 'code':
            direct.append(cell)
            continue
        source = cell['source']
        if source.startswith("run_python('src/stages/s00_intake.py')"):
            direct.append(code(prefix + 'python src/stages/s00_intake.py\npython src/stages/finalize.py S00\n'))
            direct.append(code("summarize_unit('S00')\n"))
            continue
        if source.strip() in {"run_unit('S22')", "run_unit('S23')"}:
            sid = 'S22' if 'S22' in source else 'S23'
            direct.append(code(prefix + f'python -m fpw.runner {sid}\n'))
            direct.append(code(f"summarize_unit('{sid}')\n"))
            continue
        if "run_python('fpw.check', module=True)" in source:
            cleanup, summary = source.split("run_python('fpw.check', module=True)", 1)
            direct.append(code(cleanup))
            direct.append(code(prefix + 'python -m fpw.check\n'))
            summary = summary.replace('def run_unit(sid):', 'def summarize_unit(sid):').replace("    from fpw.runner import run\n    assert run(sid) == 0, 'STOP: stage failed'\n", '')
            direct.append(code(summary.lstrip()))
            continue
        source = source.replace('import os, sys, json, hashlib, csv, runpy', 'import os, sys, json, hashlib, csv')
        if 'def run_python(' in source:
            source = source.split('def run_python(', 1)[0]
        cell['source'] = source
        direct.append(cell)
    content = direct
    for cell in content:
        if cell['cell_type'] != 'code':
            continue
        source = cell['source']
        if source.startswith(prefix):
            commands = source[len(prefix):].strip().splitlines()
            # Keep intake/finalization dependent: never finalize failed intake.
            cell['source'] = '!' + ' && '.join(commands) + '\n'
        elif source.startswith('%%bash\nset -e\ncd /content/drive/MyDrive/FoodPriceWatch\npython -m pip'):
            cell['source'] = '%pip install -q -r requirements-colab.txt\n'
        elif source.startswith('from pathlib import Path'):
            source = source.replace('os.chdir(ROOT)\n', '').replace("os.environ['PYTHONPATH'] = str(ROOT / 'src')\n", '')
            cell['source'] = '%cd /content/drive/MyDrive/FoodPriceWatch\n%env PYTHONPATH=/content/drive/MyDrive/FoodPriceWatch/src\n' + source
    # GitHub supplies code; Drive is artifact storage, never a working checkout.
    for cell in content:
        if cell['cell_type'] != 'code':
            continue
        source = cell['source']
        if source.startswith('%%bash') and 'REPO_URL=' in source:
            cell['source'] = """%%bash
set -e
if [ ! -d /content/foodprice_watch/.git ]; then
    git clone --single-branch --branch main https://github.com/mrchowdhury587/foodprice_watch.git /content/foodprice_watch
else
    git -C /content/foodprice_watch pull --ff-only origin main
fi
"""
        elif source.startswith('%cd '):
            source = source[source.index('from pathlib import Path'):]
            source = source.replace('import os, sys, json, hashlib, csv', 'import os, sys, json, hashlib, csv, shutil')
            source = source.replace("assert (ROOT / 'src/fpw/runner.py').is_file(), 'Repository is missing on Drive'", """CODE_ROOT = Path('/content/foodprice_watch')
os.environ['FPW_ARTIFACT_ROOT'] = str(ROOT)
assert (CODE_ROOT / 'src/fpw/runner.py').is_file()
ROOT.mkdir(parents=True, exist_ok=True)
# Seed only missing supporting files. Existing Drive results/state stay intact.
for directory in ['state', 'reports', 'config']:
    for original in (CODE_ROOT / directory).rglob('*'):
        if original.is_file():
            destination = ROOT / original.relative_to(CODE_ROOT)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
for name in ['DECISIONS.md', 'PROGRESS.md', 'DEVIATIONS.md']:
    if not (ROOT / name).exists():
        shutil.copy2(CODE_ROOT / name, ROOT / name)
try:
    json.loads((ROOT / 'state/stages.json').read_text())
except ValueError as error:
    raise RuntimeError('Drive stage ledger is invalid, possibly due to old merge conflicts. Preserve it and ask for recovery; do not run stages.') from error
print('Code:', CODE_ROOT, '\\nArtifacts:', ROOT)""")
            cell['source'] = '%cd /content/foodprice_watch\n%env PYTHONPATH=/content/foodprice_watch/src\n' + source.replace("sys.path.insert(0, str(ROOT / 'src'))", "sys.path.insert(0, str(CODE_ROOT / 'src'))")
    assert all('run_python(' not in c['source'] and 'run_unit(' not in c['source'] and 'subprocess' not in c['source'] for c in content)
    document = dict(notebook, cells=content, metadata=dict(notebook['metadata']))
    document['metadata']['colab'] = dict(name=name + '.ipynb')
    (directory / (name + '.ipynb')).write_text(json.dumps(document, indent=1) + '\n', encoding='utf-8')
    links.append(f'- [{name}.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/{name}.ipynb): {title}')
index = dict(notebook, cells=[markdown('# Food Price Watch notebook index\n\n' + '\n'.join(links) + '\n\nStart with 01. The old Drive checkout is no longer used for code. Preserve it until its unique edits and any conflicted artifact files have been recovered. Training and testing are not completed by this reorganization.')])
for filename in ['FoodPriceWatch_Colab.ipynb', 'FoodPriceWatch_Prediction_Resume.ipynb']:
    (ROOT / filename).write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
(directory / 'README.md').write_text('# Colab workflow\n\n' + '\n'.join(links) + '\n\nEvery workflow notebook starts with two code cells: mount Drive, then clone or pull GitHub main in /content/foodprice_watch. Existing code is updated by fast-forward only; local conflicts stop the update without deleting edits. Code lives in temporary storage; data, checkpoints, reports and stage state persist under MyDrive/FoodPriceWatch through FPW_ARTIFACT_ROOT. No Git operation runs against the old Drive repository. Keep that folder intact until its conflicting edits and artifacts have been reviewed. Package installation, checks and stage execution follow in separate sections. Invalid Drive ledger files stop initialization. Earlier sealed stages cannot be rerun in this separate-storage mode. Nothing in the old Drive checkout is deleted. Notebooks 01-05 initialize their own runtime, mount Drive, install packages and run startup checks. After reconnecting, initialize the selected notebook again. All notebooks share Drive state. Stop after each stage and paste output for review. Notebooks 02-05 mark unfinished stages explicitly; they do not train or score models. Report writing follows verified, registered results.\n', encoding='utf-8')
print('Five numbered notebooks and compatibility indexes generated.')
