"""Update the system with a longer price file (standard library only).

    python tools/update.py COMBINED.csv

Checks that COMBINED.csv (made by tools/tcb_append.py) has the same header as the current price file, contains every old report day unchanged and adds
newer days; then prints the exact steps to publish the new forecasts. It changes nothing itself. Retraining is S30 only: the model design, parameters,
alert level and the sealed test are not touched (a new test period needs a new pre-registration)."""
import csv, sys, re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cfg = (root / "config/project.yaml").read_text(encoding="utf-8")
cur = re.search(r"^price_file:\s*(\S+)", cfg, re.M).group(1)
new = Path(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
old = next((p for p in [root / "data/raw" / cur, root / "inbox" / cur, root / cur] if p.exists()), None) or sys.exit(f"current price file {cur} not found next to data/raw, inbox or the repo")
rows = lambda p: list(csv.reader(open(p, encoding="utf-8-sig")))
a, b = rows(old), rows(new)
assert a[0] == b[0], "header differs from the current price file"
da, db = {r[0]: r for r in a[1:]}, {r[0]: r for r in b[1:]}
changed = [d for d in da if d in db and da[d] != db[d]]; missing = [d for d in da if d not in db]
assert not missing and not changed, f"old report days changed or missing: {len(changed)} changed, {len(missing)} missing"
added = sorted(set(db) - set(da)); assert added, "no newer report days"
print(f"OK: {len(added)} new report days ({added[0]} .. {added[-1]}).")
print(f"""Next steps:
1. Copy {new.name} into data/raw/ on Drive (MyDrive/FoodPriceWatch/data/raw/) and set price_file: {new.name} in config/project.yaml; log it in DEVIATIONS.md; commit and push.
2. Colab notebook 01: STAGES = ['S22','S23'] (new panel and features).
3. Colab notebook 05: STAGES = ['S30'] (production fit, new forecasts, ranges, alerts).
4. Dashboard: streamlit run app/dashboard.py -- path-to-outputs/export
Note: these steps refresh the forecasts and ranges only. The alert list (alerts.csv, alert_drivers.csv) and the TCB-rise scores (S34) are NOT refreshed for the new days:
S28, S29 and S34 are finished stages with sealed results, so a later alert run needs a new pre-registration and a DEVIATIONS.md entry first.""")
