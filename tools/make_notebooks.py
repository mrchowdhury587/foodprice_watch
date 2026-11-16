"""Writes notebooks/01-05b as plain JSON (no outputs). Usage: python tools/make_notebooks.py notebooks"""
import json, sys
from pathlib import Path

OUT = Path(sys.argv[1])


def nb(cells):
    def cell(kind, text):
        lines = text.strip("\n").split("\n")
        src = [l + "\n" for l in lines[:-1]] + [lines[-1]]
        c = {"cell_type": kind, "metadata": {}, "source": src}
        if kind == "code":
            c.update(execution_count=None, outputs=[])
        return c
    return {"cells": [cell(k, t) for k, t in cells], "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}


SETUP = [
    ("code", """
from google.colab import drive
drive.mount('/content/drive')
"""),
    ("code", """
# Code comes fresh from GitHub main each session; Drive holds data and outputs only.
import os
if not os.path.isdir('/content/foodprice_watch/.git'):
    !git clone --single-branch --branch main https://github.com/mrchowdhury587/foodprice_watch.git /content/foodprice_watch
else:
    !git -C /content/foodprice_watch pull --ff-only origin main
%pip install -q -r /content/foodprice_watch/requirements-colab.txt
"""),
    ("code", """
import sys, os, json
os.chdir('/content/foodprice_watch')
sys.path.insert(0, '/content/foodprice_watch/src')
CODE_COMMIT = !git rev-parse --short HEAD
CODE_COMMIT = CODE_COMMIT[0]
from foodwatch.paths import SETTINGS, DATA_ROOT, RAW, data, raw, sha256, write_csv
# stop if Drive is not really mounted (a failed mount leaves an empty /content/drive on the Colab machine)
assert os.path.ismount('/content/drive'), 'Google Drive is not mounted: Runtime > Disconnect and delete runtime, then rerun cell 1'
assert DATA_ROOT.is_dir(), f'{DATA_ROOT} not found in Google Drive (wrong account, or the folder is missing)'
for folder in ['raw', 'processed', 'reports/tables']:
    (DATA_ROOT / folder).mkdir(parents=True, exist_ok=True)
for tmp in DATA_ROOT.rglob('*.tmp'):   # half-written files from an interrupted session
    tmp.unlink()
print('code commit:', CODE_COMMIT, '| data root:', DATA_ROOT)
"""),
]

intake = [
    ("markdown", """
# Food Price Watch 01: data intake
Copies the 4 raw files this project uses from the old Drive folder (`MyDrive/FoodPriceWatch/data/raw/project`) into `MyDrive/FoodPriceWatch_v2/raw/`, then writes `raw/MANIFEST.csv`.
Files are only copied, never edited; an existing file is never overwritten. Run the cells top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
import shutil
from pathlib import Path
OLD_RAW = Path(SETTINGS['drive']['old_raw'])
copy_log = []
for key, name in SETTINGS['raw_files'].items():
    src, dst = OLD_RAW / name, RAW / name
    if dst.exists():
        same = src.exists() and sha256(src) == sha256(dst)
        copy_log.append((name, 'already there' + ('' if same else ' (DIFFERS from old folder, kept as is)')))
    elif src.exists():
        shutil.copy2(src, dst); copy_log.append((name, 'copied'))
    else:
        copy_log.append((name, 'MISSING in old folder'))
for row in copy_log:
    print(*row, sep=': ')
assert all(raw(k).exists() for k in SETTINGS['raw_files']), 'a raw file is missing: put it into ' + str(RAW)
"""),
    ("code", """
import pandas as pd
from foodwatch import load
tables = {'prices': load.prices(), 'ramadan_eid': load.ramadan_eid(), 'fx': load.fx(), 'weather': load.weather()}
first_last = {'prices': ('Date',), 'fx': ('date',), 'weather': ('time',), 'ramadan_eid': ('ramadan_start',)}
rows = []
for key, df in tables.items():
    col = df[first_last[key][0]]
    rows.append(dict(file=SETTINGS['raw_files'][key], bytes=raw(key).stat().st_size, sha256=sha256(raw(key)), rows=len(df),
                     first=str(pd.to_datetime(col).min().date()), last=str(pd.to_datetime(col).max().date())))
manifest = pd.DataFrame(rows)
write_csv(manifest, data('manifest'))
item_ids = load.item_ids()
P = tables['prices']
found = {i: int((P.item_id == i).sum()) for i in item_ids}
"""),
    ("code", """
print('=== 01 data intake summary ===')
print('code commit:', CODE_COMMIT)
print(manifest.to_string(index=False))
print('price file: report days', P.Date.nunique(), '| items in file', P.item_id.nunique())
print('rows per focus item:', found)
print('CHECK all 8 items present:', all(n > 0 for n in found.values()))
"""),
]

processing = [
    ("markdown", """
# Food Price Watch 02: data processing
Builds the one data table for the 8 items from `MyDrive/FoodPriceWatch_v2/raw/`: TCB prices plus calendar, weather and exchange-rate columns, one row per item and report day.
Checks it and compares it with the earlier run's panel and features.
Writes `processed/data_8.csv`, `processed/checks.json` and `reports/tables/D1_panel_summary.csv` (rates only, no prices).
Needs notebook 01 to have run. Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
import pandas as pd
from foodwatch import load, panel, features, checks
items = SETTINGS['items']; ids = [i['id'] for i in items]; d = SETTINGS['drivers']
weather_items = [i['id'] for i in items if i['weather']]
fx_items = [i['id'] for i in items if i['fx']]
P = panel.build(load.prices(), ids, SETTINGS['gap_2022'])
D, avail = features.add_drivers(P, load.ramadan_eid(), load.weather(), load.fx(), weather_items=weather_items, fx_items=fx_items,
                                lag_days=d['weather_lag_days'], cap_days=d['carry_cap_days'])
dc = checks.data_checks(D, avail, len(ids), weather_items, fx_items, d['carry_cap_days'])
assert dc['ok'], dc
"""),
    ("code", """
# Regression check: the same 8 items in the earlier run's panel and features (old Drive folder). Skipped if those files are not there.
from pathlib import Path
OLD = Path(SETTINGS['drive']['old_processed'])
if (OLD / 'tcb_v2_rebuilt.parquet').exists() and (OLD / 'features_v2.parquet').exists():
    rc = checks.compare_with_old(D, pd.read_parquet(OLD / 'tcb_v2_rebuilt.parquet'), pd.read_parquet(OLD / 'features_v2.parquet'))
    assert rc['ok'], rc
else:
    rc = {'skipped': 'old panel or features not found in ' + str(OLD)}
"""),
    ("code", """
h_data = write_csv(D[features.COLUMNS], data('data'))
summary = checks.item_summary(D, {i['id']: i['group'] for i in items})
write_csv(summary, DATA_ROOT / SETTINGS['files']['tables'] / 'D1_panel_summary.csv')
record = dict(code_commit=CODE_COMMIT, data=dict(file=SETTINGS['files']['data'], sha256=h_data, column_names=features.COLUMNS, **dc),
              regression_vs_old=rc, raw_sha256={k: sha256(raw(k)) for k in SETTINGS['raw_files']})
tmp = data('checks').with_suffix('.json.tmp'); tmp.write_text(json.dumps(record, indent=2, default=str)); tmp.replace(data('checks'))
"""),
    ("code", """
print('=== 02 data processing summary ===')
print('code commit:', CODE_COMMIT)
print('data:', SETTINGS['files']['data'], '| rows', dc['rows'], '| columns', dc['columns'], '| sha256', h_data[:16], '| checks', 'PASS' if dc['ok'] else 'FAIL')
print({k: v for k, v in dc.items() if k not in ('rows', 'columns', 'ok')})
print('regression vs earlier run:', 'PASS' if rc.get('ok') else rc)
if rc.get('ok'):
    print({k: v for k, v in rc.items() if k.startswith('fx_')})
print(summary.to_string(index=False))
"""),
]

behaviour_nb = [
    ("markdown", """
# Food Price Watch 03: price behaviour
A descriptive study of the 8 prices in `processed/data_8.csv`: how often they change, how much, how long they stay unchanged, and their sustained rise episodes (the reference that alerts are scored against in notebook 05). No model.
Rules: the 2022 gap is never bridged; a blank price is "not reported", never a zero change; real jumps are kept. Rises and pre-Ramadan changes are described, not explained.
Writes tables `reports/tables/B1`-`B6` (rates, counts, sizes of changes and dates; no price series), `processed/rise_episodes_8.csv` and two figures in `reports/figures/`.
Needs notebook 02 to have run. Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
import pandas as pd
from foodwatch import behaviour as bh
D = pd.read_csv(data('data'), parse_dates=['Date'])
h_data = sha256(data('data'))
r, b = SETTINGS['rises'], SETTINGS['behaviour']
P = bh.pairs(D)
B1 = bh.change_frequency(P)
B2 = bh.change_size(P)
B3 = bh.unchanged_runs(P)
B4 = bh.price_step(P)
Rd = bh.rise_days(D, r['window_reports'])
thresholds = sorted({r['threshold'], *r['sensitivity']})
E = {t: bh.episodes(Rd, t, r['persist_reports'], r['merge_gap_reports']) for t in thresholds}
B5 = bh.episodes_by_item_year(Rd, E, r['threshold'])
B6 = bh.ramadan(Rd, D, b['ramadan_window_days'], r['window_reports'], r['threshold'])
episodes = E[r['threshold']]
"""),
    ("code", """
# Checks: no change is counted across the 2022 gap or a blank price; no rise window touches the gap.
gap_idx = D.loc[D.gap_2022, 'report_idx']
first_after_gap = D.loc[(D.Date > pd.Timestamp(SETTINGS['gap_2022'][1])), 'report_idx'].min()
chk = dict(
    changes_counted=len(P),
    change_inside_or_across_gap=int(P.report_idx.isin(gap_idx).sum() + (P.report_idx == first_after_gap).sum()),
    rise_window_touching_gap=int(Rd.R.notna()[(Rd.report_idx >= gap_idx.min()) & (Rd.report_idx - r['window_reports'] <= gap_idx.max())].sum()),
    episodes_10pct=len(episodes),
    episode_onsets_in_gap=int(episodes.onset_idx.isin(gap_idx).sum()),
)
chk['ok'] = chk['change_inside_or_across_gap'] == 0 and chk['rise_window_touching_gap'] == 0 and chk['episode_onsets_in_gap'] == 0
assert chk['ok'], chk
"""),
    ("code", """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
FIG = DATA_ROOT / SETTINGS['files']['figures']; FIG.mkdir(parents=True, exist_ok=True)
short = lambda s: s.split(' | ')[0]

# F1: share of report days with a price change, item x year (a rate, no prices)
H = B1[B1.year != 'all'].pivot(index='item_id', columns='year', values='share_changed')
fig, ax = plt.subplots(figsize=(7.5, 4))
im = ax.imshow(H.values, cmap='Blues', vmin=0, vmax=0.6, aspect='auto')
# year labels show the months covered: 2022 counts only the days before the gap
used = D[~D.gap_2022 & (D.Date < pd.Timestamp(SETTINGS['gap_2022'][0])) | (D.Date > pd.Timestamp(SETTINGS['gap_2022'][1]))]
span = used.groupby(used.Date.dt.year).Date.agg(['min', 'max'])
full = lambda y: span.loc[y, 'min'].month == 1 and span.loc[y, 'max'].month == 12
lab = [y if full(int(y)) else y + chr(10) + span.loc[int(y), 'min'].strftime('%b') + '-' + span.loc[int(y), 'max'].strftime('%b') for y in H.columns]
ax.set_xticks(range(H.shape[1]), lab); ax.set_yticks(range(H.shape[0]), [short(i) for i in H.index])
for (i, j), v in pd.DataFrame(H.values).stack().items():
    ax.text(j, i, f'{v:.2f}', ha='center', va='center', fontsize=8, color='white' if v > 0.4 else '#1a1a1a')
ax.set_title('Share of report days on which the price changed', loc='left', fontsize=11)
for s in ax.spines.values(): s.set_visible(False)
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout(); fig.savefig(FIG / 'F1_change_frequency.png', dpi=160); plt.close(fig)

# F2: price series with sustained rise episodes shaded (contains prices: stays on Drive)
items = list(H.index)
fig, axes = plt.subplots(4, 2, figsize=(11, 10), sharex=True)
g0, g1 = pd.Timestamp(SETTINGS['gap_2022'][0]), pd.Timestamp(SETTINGS['gap_2022'][1])
for ax, item in zip(axes.flat, items):
    x = D[(D.item_id == item) & ~D.gap_2022]
    pre, post = x[x.Date < g0], x[x.Date > g1]
    for part in (pre, post):
        ax.plot(part.Date, part.Price_Avg, color='#2a6fb0', lw=1.2)
    ax.axvspan(g0, g1, color='#d9d9d9', alpha=0.6, lw=0)
    for e in episodes[episodes.item_id == item].itertuples():
        ax.axvspan(e.onset_date, e.end_date, color='#e07b39', alpha=0.35, lw=0)
    ax.set_title(item, loc='left', fontsize=9)
    ax.tick_params(labelsize=8)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
fig.suptitle('Daily price (Tk) with sustained 10 % rise episodes (orange); 2022 gap in grey', x=0.01, ha='left', fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'F2_prices_with_rises.png', dpi=160); plt.close(fig)
"""),
    ("code", """
T = DATA_ROOT / SETTINGS['files']['tables']
for name, df in [('B1_change_frequency', B1), ('B2_change_size', B2), ('B3_unchanged_runs', B3), ('B4_price_step', B4),
                 ('B5_rise_episodes_by_item_year', B5), ('B6_ramadan', B6)]:
    write_csv(df, T / f'{name}.csv')
h_eps = write_csv(episodes.assign(onset_date=episodes.onset_date.dt.date, end_date=episodes.end_date.dt.date), data('rise_episodes'))
"""),
    ("code", """
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
P2 = lambda df: df.assign(item_id=df.item_id.map(short)).to_string(index=False)
yr = lambda y: B5.year.between(*y)
print('=== 03 price behaviour summary ===')
print('code commit:', CODE_COMMIT, '| data_8.csv sha256', h_data[:16])
print('checks:', 'PASS' if chk['ok'] else 'FAIL', {k: v for k, v in chk.items() if k != 'ok'})
print('rise rule: R over', r['window_reports'], 'report days >=', r['threshold'], 'for >=', r['persist_reports'], 'report days; merge gap', r['merge_gap_reports'])
print('\\nB1 share of report days with a change, by year (2021 from 17 May; 2022 = 1 Jan to 11 Mar, before the gap; 2026 to 24 Oct)')
print(P2(B1.pivot(index='item_id', columns='year', values='share_changed').reset_index()))
print('\\nB2 size of a change (on days it changed)'); print(P2(B2))
print('\\nB3 unchanged runs (report days)'); print(P2(B3))
print('\\nB4 price step (Tk)'); print(P2(B4))
print('\\nB5 sustained rise episodes by onset year (10 % rule)')
print(P2(B5.pivot(index='item_id', columns='year', values='episodes_10pct').fillna(0).astype(int).reset_index()))
for lab, y in [('validation 2024', (2024, 2024)), ('retrospective 2025-26', (2025, 2026))]:
    s = B5[yr(y)]
    print(f'{lab}: episodes 7 % / 10 % / 15 % =', int(s.episodes_7pct.sum()), '/', int(s.episodes_10pct.sum()), '/', int(s.episodes_15pct.sum()),
          '| items with no 10 % episode:', sorted(short(i) for i in set(D.item_id) - set(s.loc[s.episodes_10pct > 0, 'item_id'])))
print('\\nB6 before Ramadan vs other days (descriptive;', B6.attrs['window'] + ')'); print(P2(B6))
print('\\nrise episodes file:', SETTINGS['files']['rise_episodes'], '| rows', len(episodes), '| sha256', h_eps[:16])
print('figures:', sorted(p.name for p in FIG.glob('*.png')))
"""),
]

choice_nb = [
    ("markdown", """
# Food Price Watch 04a: forecast choice on 2024
Compares "tomorrow = today" (naive), ETS and 16 LightGBM configurations (2 feature sets x 8 settings) on the **2024 validation year only**, at horizons 1, 7, 14 and 30 report days.
Picks the LightGBM configuration with the lowest relative error against naive (a simpler one within 1 % wins). No 2025-26 target is used here.
The choice is copied into `config/settings.yaml` (`forecast_choice`) and committed **before** notebook 04b scores 2025-26.
Writes `reports/tables/M1_validation_grid.csv` and `M2_validation_models.csv` (errors and ratios only). Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
import pandas as pd
from foodwatch import forecast as fc, metrics as mt
D = pd.read_csv(data('data'), parse_dates=['Date'])
h_data = sha256(data('data'))
f = SETTINGS['forecast']; H = f['horizons']
S = fc.prepare(D, H, f['lags'], f['rolling'], f['rolling_min_periods'])
L = fc.stack(S, H)
dates = D.drop_duplicates('report_idx').set_index('report_idx').Date
val_start, val_end = SETTINGS['periods']['validation']
origins = fc.period_origins(dates, val_start, val_end, f['origin_step'], max(H))
print('validation origins:', len(origins), '|', dates[origins[0]].date(), 'to', dates[origins[-1]].date())
"""),
    ("code", """
# naive, ETS and the 16 LightGBM configurations on the 2024 origins
runs = [fc.rolling_forecasts(L, origins, fc.feature_columns('price_only', f['lags'], f['rolling']), fc.fit_naive, 10**9, 'naive'),
        fc.ets_forecasts(S, L, origins, H)]
configs = fc.grid(f['grid'])
for i, cfg in enumerate(configs):
    cols = fc.feature_columns(cfg['feature_set'], f['lags'], f['rolling'])
    runs.append(fc.rolling_forecasts(L, origins, cols, fc.make_fit_lgbm(cfg['params'], f['rounds']), f['refit_every'], cfg['config']))
    print(f'{i + 1}/{len(configs)}', cfg['config'])
V = pd.concat(runs, ignore_index=True)
"""),
    ("code", """
# Checks: only 2024 targets are scored; no training target after its fitting origin; nothing touches the 2022 gap; naive = 1.
Vs = mt.scored(V)
chk = dict(
    forecasts=len(V), scored=len(Vs),
    last_target_date=str(dates[int(Vs.target_idx.max())].date()),
    target_after_validation_year=int((Vs.target_idx.map(dates) > pd.Timestamp(val_end)).sum()),
    fit_after_origin=int((V.fit_cutoff > V.cutoff).sum()),
    rows_touching_gap=int(L.loc[L.report_idx.isin(origins), ['touch_gap', 'tgap']].any(axis=1).sum()),
    naive_rel_mae=round(float(mt.gmean_rel(V[V.model == 'naive']).gmean_rel_mae.max()), 6),
)
chk['ok'] = (chk['target_after_validation_year'] == 0 and chk['fit_after_origin'] == 0 and chk['rows_touching_gap'] == 0
             and chk['naive_rel_mae'] == 1.0)
assert chk['ok'], chk
"""),
    ("code", """
# Choice: geometric mean over items and horizons of the relative MAE against naive; a simpler configuration within the margin wins.
R = mt.rel_mae_by_item(V)
overall = R.groupby('model').rel.apply(mt.gmean)
order = [c['config'] for c in configs]
chosen = fc.choose(overall[order].to_dict(), order, f['tie_margin'])
cfg = next(c for c in configs if c['config'] == chosen)
G = mt.gmean_rel(V)
M1 = (G[G.model.isin(order)].pivot(index='model', columns='horizon', values='gmean_rel_mae').add_prefix('rel_h').reset_index()
      .assign(rel_all=lambda t: t.model.map(overall)).rename(columns={'model': 'config'}))
M1 = M1.set_index('config').loc[order].reset_index().round(4)
M1['chosen'] = M1.config == chosen
keep = V[V.model.isin(['naive', 'ets', chosen])].replace({'model': {chosen: 'lgbm'}})
M2 = mt.summary(keep).merge(mt.gmean_rel(keep), on=['model', 'horizon']).merge(mt.dm_vs_naive(keep), on=['model', 'horizon'], how='left')
M2 = M2.round(5)
T = DATA_ROOT / SETTINGS['files']['tables']
write_csv(M1, T / 'M1_validation_grid.csv')
write_csv(M2, T / 'M2_validation_models.csv')
"""),
    ("code", """
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print('=== 04a forecast choice on 2024 (validation year only) ===')
print('code commit:', CODE_COMMIT, '| data_8.csv sha256', h_data[:16])
print('checks:', 'PASS' if chk['ok'] else 'FAIL', {k: v for k, v in chk.items() if k != 'ok'})
print('origins:', len(origins), '| horizons', H, '| rel = MAE of the model / MAE of "tomorrow = today" (below 1 = better than naive)')
print('\\nM1 LightGBM grid, geometric mean relative MAE over items (simplest first)')
print(M1.to_string(index=False))
print('\\nM2 naive, ETS and the chosen LightGBM by horizon (2024); dm_stat > 0 = worse than naive, < 0 = better; p_holm = Holm-corrected p; NaN = not computable')
print(M2[['model', 'horizon', 'n', 'mae_log', 'mae_log_naive', 'gmean_rel_mae', 'mae_tk', 'mae_tk_naive', 'accuracy', 'accuracy_naive',
          'direction_acc', 'dm_stat', 'p_holm']].to_string(index=False))
for m in ['ets', 'lgbm']:
    beats = [h for h in H if M2.loc[(M2.model == m) & (M2.horizon == h), 'gmean_rel_mae'].iloc[0] < 1]
    print(f'{m}: below naive at horizons {beats if beats else "none"}')
print('\\nCHOICE (to be committed before 04b):')
print('forecast_choice:')
print(f"  config: {chosen}")
print(f"  feature_set: {cfg['feature_set']}")
print(f"  params: {cfg['params']}")
print(f"  validation_rel_mae: {round(float(overall[chosen]), 4)}")
print(f"  chosen_by: notebook 04a, code {CODE_COMMIT}, 2024 origins only")
"""),
]

test_nb = [
    ("markdown", """
# Food Price Watch 04b: forecast test on 2025-26 (retrospective)
Scores "tomorrow = today" (naive), ETS and the LightGBM configuration chosen on 2024 (notebook 04a, fixed in `config/settings.yaml` `forecast_choice`) on weekly origins from 2025-01-01 to 2026-10-24.
2025-26 was already looked at by the earlier run, so every result here is **retrospective**. Every figure sits beside the naive figure.
Also makes the 7-day forecasts from every report day since 2023-06-01 that notebook 05 uses for the alert ranges.
Writes `reports/tables/M3_test_accuracy.csv`, `M4_test_by_item.csv` (errors and ratios only), `processed/forecasts_test.csv` and `processed/forecasts_h7.csv` (contain prices: Drive only). Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
# The choice must have been fixed and committed before this notebook scores anything.
import subprocess
choice = SETTINGS.get('forecast_choice') or {}
assert choice.get('config') and choice.get('params'), 'forecast_choice is empty: run 04a and commit its choice first'
choice_commit = subprocess.run(['git', 'log', '--reverse', '--format=%h %ad', '--date=short', '-S', choice['config'], '--', 'config/settings.yaml'],
                               capture_output=True, text=True).stdout.strip()
choice_commit = choice_commit.splitlines()[0] if choice_commit else 'not found in git history'
print('chosen on 2024:', choice['config'], '| choice first committed in', choice_commit)
"""),
    ("code", """
import numpy as np
import pandas as pd
from foodwatch import forecast as fc, metrics as mt
D = pd.read_csv(data('data'), parse_dates=['Date'])
h_data = sha256(data('data'))
f = SETTINGS['forecast']; H = f['horizons']
S = fc.prepare(D, H, f['lags'], f['rolling'], f['rolling_min_periods'])
L = fc.stack(S, H)
dates = D.drop_duplicates('report_idx').set_index('report_idx').Date
test_start, test_end = SETTINGS['periods']['test']
origins = fc.period_origins(dates, test_start, test_end, f['origin_step'], max(H))
cols = fc.feature_columns(choice['feature_set'], f['lags'], f['rolling'])
fit_lgbm = fc.make_fit_lgbm(choice['params'], f['rounds'])
Tst = pd.concat([fc.rolling_forecasts(L, origins, cols, fc.fit_naive, 10**9, 'naive'),
                 fc.ets_forecasts(S, L, origins, H),
                 fc.rolling_forecasts(L, origins, cols, fit_lgbm, f['refit_every'], 'lgbm')], ignore_index=True)
print('test origins:', len(origins), '|', dates[origins[0]].date(), 'to', dates[origins[-1]].date())
"""),
    ("code", """
# 7-day forecasts from every report day since daily_h7.start, for the alert ranges (notebook 05). Naive = today's price.
dh = f['daily_h7']
F7 = fc.daily_h7(L, dates, cols, fit_lgbm, dh['start'], dh['refit_every'])
F7 = pd.concat([F7, F7.assign(pred=0.0, forecast=lambda x: np.exp(x.lp_origin), model='naive')], ignore_index=True)
F7['origin_date'] = F7.cutoff.map(dates); F7['target_date'] = F7.target_idx.map(dates)
"""),
    ("code", """
# Checks: no model fitted after its origin; only 2025-26 targets scored; nothing touches the 2022 gap; naive = 1;
# the 7-day file has one row per item, model and report day with a price (or carried price) since its start.
Ts = mt.scored(Tst)
expected7 = int(S[(S.report_idx.map(dates) >= pd.Timestamp(dh['start'])) & S.lp.notna()].shape[0])
chk = dict(
    test_forecasts=len(Tst), test_scored=len(Ts),
    first_target_date=str(dates[int(Ts.target_idx.min())].date()), last_target_date=str(dates[int(Ts.target_idx.max())].date()),
    target_before_test=int((Ts.target_idx.map(dates) < pd.Timestamp(test_start)).sum()),
    fit_after_origin=int((Tst.fit_cutoff > Tst.cutoff).sum() + (F7.fit_cutoff > F7.cutoff).sum()),
    rows_touching_gap=int(L.loc[L.report_idx.isin(origins), ['touch_gap', 'tgap']].any(axis=1).sum()),
    naive_rel_mae=round(float(mt.gmean_rel(Tst[Tst.model == 'naive']).gmean_rel_mae.max()), 6),
    h7_rows_per_model=int(len(F7) / 2), h7_rows_expected=expected7,
    h7_first_origin=str(F7.origin_date.min().date()), h7_last_origin=str(F7.origin_date.max().date()),
)
chk['ok'] = (chk['target_before_test'] == 0 and chk['fit_after_origin'] == 0 and chk['rows_touching_gap'] == 0
             and chk['naive_rel_mae'] == 1.0 and chk['h7_rows_per_model'] == expected7)
assert chk['ok'], chk
"""),
    ("code", """
M3 = (mt.summary(Tst).merge(mt.gmean_rel(Tst), on=['model', 'horizon']).merge(mt.dm_vs_naive(Tst), on=['model', 'horizon'], how='left')
      .assign(period='2025-01-01 to 2026-10-24 (retrospective)')).round(5)
R = mt.rel_mae_by_item(Tst)
acc = mt.scored(Tst).groupby(['model', 'item_id', 'horizon']).apply(
    lambda g: pd.Series(dict(accuracy=1 - float(((g.forecast - g.actual).abs() / g.actual).mean()))), include_groups=False).reset_index()
M4 = R.merge(acc, on=['model', 'item_id', 'horizon']).rename(columns={'mae': 'mae_log', 'naive': 'mae_log_naive', 'rel': 'rel_mae'})
M4 = M4.assign(period='retrospective').round(5)
T = DATA_ROOT / SETTINGS['files']['tables']
write_csv(M3, T / 'M3_test_accuracy.csv')
write_csv(M4, T / 'M4_test_by_item.csv')
h_test = write_csv(Tst, data('forecasts_test'))
h_h7 = write_csv(F7, data('forecasts_h7'))
"""),
    ("code", """
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
short = lambda s: s.split(' | ')[0]
print('=== 04b forecast test, 2025-01-01 to 2026-10-24: RETROSPECTIVE ===')
print('code commit:', CODE_COMMIT, '| data_8.csv sha256', h_data[:16])
print('model choice (2024 only):', choice['config'], '| choice first committed in', choice_commit)
print('checks:', 'PASS' if chk['ok'] else 'FAIL', {k: v for k, v in chk.items() if k != 'ok'})
print('\\nM3 accuracy by model and horizon; rel = MAE / MAE of "tomorrow = today"; dm_stat > 0 = worse than naive; NaN = not computable')
print(M3[['model', 'horizon', 'n', 'mae_log', 'mae_log_naive', 'gmean_rel_mae', 'mae_tk', 'mae_tk_naive', 'accuracy', 'accuracy_naive',
          'direction_acc', 'dm_stat', 'p_holm']].to_string(index=False))
for m in ['ets', 'lgbm']:
    beats = [h for h in H if M3.loc[(M3.model == m) & (M3.horizon == h), 'gmean_rel_mae'].iloc[0] < 1]
    sig = [h for h in H if (M3.loc[(M3.model == m) & (M3.horizon == h), 'dm_stat'].iloc[0] < 0) and (M3.loc[(M3.model == m) & (M3.horizon == h), 'p_holm'].iloc[0] < 0.05)]
    print(f'{m}: below naive at horizons {beats if beats else "none"}; significantly better (DM, Holm p < 0.05) at {sig if sig else "none"}')
print('\\nM4 relative MAE by item at horizon 7 (below 1 = better than naive)')
print(M4[M4.horizon == 7].pivot(index='item_id', columns='model', values='rel_mae').rename(index=short).round(3).to_string())
print('\\nfiles:', SETTINGS['files']['forecasts_test'], 'sha256', h_test[:16], '|', SETTINGS['files']['forecasts_h7'], 'sha256', h_h7[:16], '| rows', len(F7))
"""),
]

alert_choice_nb = [
    ("markdown", """
# Food Price Watch 05a: alert settings chosen on 2024
Three ways to raise an abnormal-rise alert, all with the same persistence (above the bound on 3 of the last 5 report days, 7-report horizon):
A. ML range (LightGBM forecast errors), B. simple range ("tomorrow = today", so the 7-report change), C. fixed 7-report rise threshold.
For each rule the most sensitive candidate whose 2024 alert runs that match no sustained 10 % rise stay at or below 2 per item-year is chosen. Only 2024 is used.
The choice goes into `config/settings.yaml` (`alert_choice`) and is committed **before** notebook 05b scores anything.
Needs notebooks 03 and 04b. Writes `reports/tables/A1_alert_choice.csv` (counts and rates only). Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
import numpy as np
import pandas as pd
from foodwatch import alerts as al, behaviour as bh
a, r = SETTINGS['alerts'], SETTINGS['rises']
k, m, hz = a['persistence']['k'], a['persistence']['m'], a['horizon']
before, after = a['match']['before_reports'], a['match']['after_reports']
VAL = SETTINGS['periods']['validation']
D = pd.read_csv(data('data'), parse_dates=['Date'])
F7 = pd.read_csv(data('forecasts_h7'))
h_f7 = sha256(data('forecasts_h7'))
EP = bh.episodes(bh.rise_days(D, r['window_reports']), r['threshold'], r['persist_reports'], r['merge_gap_reports'])
P = {'A': al.bounds(al.table(F7, 'lgbm', hz), hz, a['levels'], a['window'], a['min_obs']),
     'B': al.bounds(al.table(F7, 'naive', hz), hz, a['levels'], a['window'], a['min_obs'])}
P['C'] = P['B']
eps24 = al.in_period(EP, 'onset_date', VAL)
"""),
    ("code", """
# Checks: one row per item and report day (so shifting by 7 rows = errors whose target is <= the origin); naive error = the change;
# the rise episodes equal notebook 03's file; enough 2024 episodes; nothing in the 2022 gap.
old = pd.read_csv(data('rise_episodes'))
chk = dict(
    rows_lgbm=len(P['A']), rows_naive=len(P['B']),
    one_row_per_report_day=al.consecutive(P['A']) and al.consecutive(P['B']),
    naive_error_is_change=bool(np.allclose(P['B'].resid.dropna(), P['B'].y.dropna())),
    episodes_same_as_03=bool(len(old) == len(EP) and (old[['item_id', 'onset_idx', 'end_idx']].values == EP[['item_id', 'onset_idx', 'end_idx']].values).all()),
    episodes_2024=len(eps24),
    first_target_date=str(P['A'].tdate.min().date()),
    first_bound_date=str(P['A'].loc[P['A'][f"hi{a['levels'][0]}"].notna(), 'tdate'].min().date()),
)
chk['ok'] = chk['one_row_per_report_day'] and chk['naive_error_is_change'] and chk['episodes_same_as_03'] and chk['episodes_2024'] >= 5
assert chk['ok'], chk
"""),
    ("code", """
# Every candidate on 2024: alert runs, runs matching no rise per item-year, recall
iy = al.item_years(P['B'], VAL)
rows = []
for rule, cands in [('A', a['levels']), ('B', a['levels']), ('C', a['thresholds'])]:
    for s in sorted(cands):
        _, on = al.range_alerts(P[rule], s, k, m) if rule != 'C' else al.threshold_alerts(P[rule], s, k, m)
        rn = al.in_period(al.runs(P[rule], on), 'start_date', VAL)
        e, rn = al.match(rn, eps24, before, after)
        rows.append(dict(rule=rule, setting=s, **al.prf(e, rn, iy)))
A1 = pd.DataFrame(rows)
choice = {}
for rule in 'ABC':
    t = A1[A1.rule == rule].set_index('setting')
    s, met = al.choose(t.unmatched_per_item_year.to_dict(), sorted(t.index), a['fa_target_per_item_year'])
    choice[rule] = dict(setting=float(s), target_met=met)
A1['chosen'] = [choice[r_]['setting'] == s for r_, s in zip(A1.rule, A1.setting)]
A1 = A1.round(4)
write_csv(A1, DATA_ROOT / SETTINGS['files']['tables'] / 'A1_alert_choice.csv')
"""),
    ("code", """
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
names = {'A': 'ML range (LightGBM)', 'B': 'simple range ("tomorrow = today")', 'C': 'fixed 7-report rise'}
print('=== 05a alert settings chosen on 2024 (validation year only) ===')
print('code commit:', CODE_COMMIT, '| forecasts_h7.csv sha256', h_f7[:16])
print('checks:', 'PASS' if chk['ok'] else 'FAIL', {k_: v for k_, v in chk.items() if k_ != 'ok'})
print('2024: episodes', len(eps24), '| item-years', round(iy, 2), '| target: runs matching no rise <=', a['fa_target_per_item_year'], 'per item-year')
print('\\nA1 every candidate on 2024 (setting = range level for A and B, threshold for C)')
print(A1[['rule', 'setting', 'episodes', 'detected', 'recall', 'alert_runs', 'matched_runs', 'precision', 'unmatched_per_item_year',
          'median_delay_reports', 'chosen']].to_string(index=False))
print('\\nCHOICE (to be committed before 05b):')
print('alert_choice:')
for rule in 'ABC':
    print(f"  {rule}: {{setting: {choice[rule]['setting']}, target_met: {str(choice[rule]['target_met']).lower()}}}   # {names[rule]}")
print(f"  chosen_by: notebook 05a, code {CODE_COMMIT}, 2024 only")
"""),
]

alert_scoring_nb = [
    ("markdown", """
# Food Price Watch 05b: alert rules scored against sustained rises
Scores the three alert rules with the settings fixed on 2024 (notebook 05a, `config/settings.yaml` `alert_choice`) against the sustained 10 % rise episodes of notebook 03:
A. ML range (LightGBM), B. simple range ("tomorrow = today"), C. fixed 7-report rise (a reference point: it is close to the rise definition itself).
Periods: 2024 (validation, the year the settings were chosen on) and 2025-01-01 to 2026-10-24 (**retrospective**: the earlier run already looked at it).
Alerts are abnormal-rise detection, not early warning. Writes tables `A2`-`A5` (counts and rates) and `processed/alerts_8.csv` (Drive only). Run top to bottom and paste the last cell's output back.
"""),
    *SETUP,
    ("code", """
# The settings must have been fixed and committed before this notebook scores anything.
import subprocess
choice = SETTINGS.get('alert_choice') or {}
assert all(r_ in choice and 'setting' in choice[r_] for r_ in 'ABC'), 'alert_choice is empty: run 05a and commit its choice first'
log = subprocess.run(['git', 'log', '--reverse', '--format=%h %ad', '--date=short', '-S', 'alert_choice:', '--', 'config/settings.yaml'],
                     capture_output=True, text=True).stdout.strip().splitlines()
fixed = subprocess.run(['git', 'log', '--reverse', '--format=%h %ad', '--date=short', '-S', 'A: {setting:', '--', 'config/settings.yaml'],
                       capture_output=True, text=True).stdout.strip().splitlines()
choice_commit = fixed[0] if fixed else 'not found in git history'
print('settings (chosen on 2024):', {r_: choice[r_]['setting'] for r_ in 'ABC'}, '| first committed in', choice_commit)
"""),
    ("code", """
import numpy as np
import pandas as pd
from foodwatch import alerts as al, behaviour as bh
a, r = SETTINGS['alerts'], SETTINGS['rises']
k, m, hz = a['persistence']['k'], a['persistence']['m'], a['horizon']
before, after = a['match']['before_reports'], a['match']['after_reports']
PERIODS = {'2024 validation': SETTINGS['periods']['validation'], '2025-26 retrospective': SETTINGS['periods']['test']}
D = pd.read_csv(data('data'), parse_dates=['Date'])
F7 = pd.read_csv(data('forecasts_h7'))
h_f7 = sha256(data('forecasts_h7'))
EP = bh.episodes(bh.rise_days(D, r['window_reports']), r['threshold'], r['persist_reports'], r['merge_gap_reports'])
P = {'A': al.bounds(al.table(F7, 'lgbm', hz), hz, a['levels'], a['window'], a['min_obs']),
     'B': al.bounds(al.table(F7, 'naive', hz), hz, a['levels'], a['window'], a['min_obs'])}
P['C'] = P['B']
EX, ON, RUNS = {}, {}, {}
for rule in 'ABC':
    s = choice[rule]['setting']
    EX[rule], ON[rule] = al.range_alerts(P[rule], s, k, m) if rule != 'C' else al.threshold_alerts(P[rule], s, k, m)
    RUNS[rule] = al.runs(P[rule], ON[rule])
"""),
    ("code", """
# Score every rule in both periods; overlap of A and B; range coverage; per item.
rows, ov, cov, per_item, matched = [], [], [], [], {}
for pname, per in PERIODS.items():
    eps = al.in_period(EP, 'onset_date', per)
    iy = al.item_years(P['B'], per)
    tday = al.in_period(P['B'], 'tdate', per).target_idx
    lo, hi = int(tday.min()), int(tday.max())
    for rule in 'ABC':
        rn = al.in_period(RUNS[rule], 'start_date', per)
        e, rn2 = al.match(rn, eps, before, after)
        matched[(pname, rule)] = e
        rows.append(dict(period=pname, rule=rule, setting=choice[rule]['setting'], **al.prf(e, rn2, iy),
                         **al.placebo(rn, eps, before, after, lo, hi, a['placebo_draws'])))
        for it in sorted(P['B'].item_id.unique()):
            per_item.append(dict(period=pname, rule=rule, item_id=it, episodes=int((e.item_id == it).sum()),
                                 detected=int(e[e.item_id == it].detected.sum()), alert_runs=int((rn2.item_id == it).sum())))
    ov.append(dict(period=pname, **al.overlap(matched[(pname, 'A')], matched[(pname, 'B')])))
    for rule in 'AB':
        cov.append(dict(period=pname, rule=rule, **al.coverage(P[rule], choice[rule]['setting'], per)))
A2 = pd.DataFrame(rows).round(4); A3 = pd.DataFrame(ov); A4 = pd.DataFrame(cov).round(4); A5 = pd.DataFrame(per_item)
"""),
    ("code", """
# Checks: placebo p valid; runs and episodes inside their period; 2024 results equal 05a's chosen rows; nothing before the forecasts start.
A1 = pd.read_csv(DATA_ROOT / SETTINGS['files']['tables'] / 'A1_alert_choice.csv')
a1 = A1[A1.chosen.astype(str).str.lower() == 'true'].set_index('rule')
v = A2[A2.period == '2024 validation'].set_index('rule')
both = P['A'][['item_id', 'target_idx', 'resid']].merge(P['B'][['item_id', 'target_idx', 'resid']], on=['item_id', 'target_idx']).dropna()
chk = dict(
    placebo_p_valid=bool(A2.placebo_p.between(0, 1, inclusive='right').all()),
    same_as_05a=bool(all(int(v.loc[r_, 'detected']) == int(a1.loc[r_, 'detected']) and int(v.loc[r_, 'alert_runs']) == int(a1.loc[r_, 'alert_runs']) for r_ in 'ABC')),
    first_alert_date=str(min(RUNS[r_].start_date.min() for r_ in 'ABC').date()),
    episodes_per_period={p_: int(len(al.in_period(EP, 'onset_date', per))) for p_, per in PERIODS.items()},
    corr_errors_A_B=round(float(np.corrcoef(both.resid_x, both.resid_y)[0, 1]), 4),
)
chk['ok'] = chk['placebo_p_valid'] and chk['same_as_05a']
assert chk['ok'], chk
"""),
    ("code", """
T = DATA_ROOT / SETTINGS['files']['tables']
for name, df in [('A2_rule_comparison', A2), ('A3_rule_overlap', A3), ('A4_range_coverage', A4), ('A5_alerts_by_item', A5)]:
    write_csv(df, T / f'{name}.csv')
alerts_long = pd.concat([P[r_][['item_id', 'target_date', 'target_idx']].assign(rule=r_, exceed=EX[r_].values, alert=ON[r_].values) for r_ in 'ABC'],
                        ignore_index=True)
h_al = write_csv(alerts_long, data('alerts'))
"""),
    ("code", """
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
names = {'A': 'ML range', 'B': 'simple range', 'C': 'fixed 7-report rise'}
print('=== 05b alert rules vs sustained 10 % rises: 2024 validation and 2025-26 RETROSPECTIVE ===')
print('code commit:', CODE_COMMIT, '| forecasts_h7.csv sha256', h_f7[:16])
print('settings fixed on 2024:', {r_: choice[r_]['setting'] for r_ in 'ABC'}, '| first committed in', choice_commit)
print('checks:', 'PASS' if chk['ok'] else 'FAIL', {k_: v_ for k_, v_ in chk.items() if k_ != 'ok'})
print('\\nA2 rule comparison (recall = rises caught; precision = alert runs that match a rise; delay in report days after onset)')
print(A2[['period', 'rule', 'setting', 'episodes', 'detected', 'recall', 'placebo_recall', 'placebo_p', 'alert_runs', 'precision', 'f1',
          'median_delay_reports', 'runs_per_item_year', 'unmatched_per_item_year']].to_string(index=False))
print('\\nA3 rises caught by the ML range (A) and the simple range (B)'); print(A3.to_string(index=False))
print('\\nA4 range coverage (share of days at or below the upper bound; nominal = level)'); print(A4.to_string(index=False))
print('\\nA5 per item: rises caught / episodes (alert runs)')
A5v = A5.assign(cell=A5.detected.astype(str) + '/' + A5.episodes.astype(str) + ' (' + A5.alert_runs.astype(str) + ')')
print(A5v.pivot_table(index='item_id', columns=['period', 'rule'], values='cell', aggfunc='first').rename(index=lambda s: s.split(' | ')[0]).to_string())
print()
for pname in PERIODS:
    x = A2[A2.period == pname].set_index('rule')
    for r_ in 'ABC':
        print(f"{pname} | {r_} {names[r_]}: caught {int(x.loc[r_, 'detected'])}/{int(x.loc[r_, 'episodes'])} = {x.loc[r_, 'recall']:.2f} "
              f"vs random dates {x.loc[r_, 'placebo_recall']:.2f} (p = {x.loc[r_, 'placebo_p']:.3f}); {int(x.loc[r_, 'alert_runs'])} alert runs")
    nb_, na_ = int(x.loc['B', 'detected']), int(x.loc['A', 'detected'])
    cmp_ = 'more rises than' if nb_ > na_ else ('as many rises as' if nb_ == na_ else 'fewer rises than')
    print(f"{pname}: the simple range catches {cmp_} the ML range ({nb_} vs {na_})")
print('\\nalerts file:', SETTINGS['files']['alerts'], '| rows', len(alerts_long), '| sha256', h_al[:16])
"""),
]

OUT.mkdir(parents=True, exist_ok=True)
for name, cells in [("01_data_intake.ipynb", intake), ("02_data_processing.ipynb", processing), ("03_price_behaviour.ipynb", behaviour_nb),
                    ("04a_forecast_choice.ipynb", choice_nb), ("04b_forecast_test.ipynb", test_nb), ("05a_alert_choice.ipynb", alert_choice_nb), ("05b_alert_scoring.ipynb", alert_scoring_nb)]:
    (OUT / name).write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT / name)
