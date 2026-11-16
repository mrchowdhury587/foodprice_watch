# Project plan, 2026-11-17

**Title:** Food Price Watch: A Monitoring and Abnormal-Rise Alert System for Daily Retail Food Prices in Dhaka

> **Update 2026-11-17 (later the same day):** the user chose a fresh restart instead of adding stages S36-S39 to the old pipeline. The old pipeline is archived in `archive/old_pipeline/`. The work now runs as one Colab notebook per task on 8 items (`notebooks/`, `src/foodwatch/`, `config/settings.yaml`); see `DEVIATIONS.md`. The analyses below (alert-rule comparison, price behaviour, focus items, report) and the claims lists still apply; the stage numbers, `stages.json` and `config/project.yaml` references do not.

This plan replaces `docs/PROJECT_PLAN_2026-11-15.md` where they differ. It was approved by the user on 2026-11-17. Every difference must be logged in `DEVIATIONS.md` before code is written (step 0).

## 1. What changes and what does not

The project stops presenting itself as a price prediction system. It becomes a monitoring and alert system, with the forecast models reported as a benchmark.

Nothing is rebuilt. The data pipeline, the model, the ranges, the alerts, the driver breakdown, the dashboard and every existing result table stay exactly as they are. Three analysis stages and a new report are added.

| Part | Source | Status |
|---|---|---|
| Dataset and audit | S22 | done, kept |
| Six-model benchmark and sealed test | S25 to S27 | done, kept; reported honestly as "no model beat tomorrow = today" |
| Ranges and alerts | S28 | done, kept |
| Driver breakdown | S29 | done, kept; reported with its instability |
| Alerts judged against TCB price rises | S34 | done, kept |
| **Alert-rule comparison** | **S36, new** | to build |
| **Price behaviour study** | **S37, new** | to build |
| **Focus-item tables (8 items)** | **S38, new** | to build |
| **Report and docs for the new title** | **S39, new** | to write |

A backup of the whole checkout as it stood before this plan is at `E:\msc_project\foodprice_watch_backup_2026-11-17` (local git tag `backup-2026-11-17`).

## 2. Why this plan

Checked against the committed tables on 2026-11-16 and 17:

- The model does not beat "tomorrow = today": relative error 1.01 at 1 report day and 1.00 at 7, 14 and 30 (`P7_accuracy_by_horizon.csv`). It is slightly but measurably worse at 1 and 7 days (`P7_dm_vs_naive.csv`).
- On 2024 validation the simple baseline ranked first of six (`P5_model_selection_overall.csv`).
- The alerts catch 65 % (2024) and 75 % (2025-26) of sustained 10 % rises against 23 to 25 % for random dates, but only about 20 % of alert runs match a rise and the median delay is 2 report days (`P10_alerts_vs_rises.csv`).
- News-dated shock events are not detected better than chance: 11 of 16, placebo mean 0.59, p = 0.26 (`P8_alert_summary.csv`).
- The driver breakdown is unstable: the weather share was 0.47, 0.61 and 0.04 across three refits (`P9_driver_stability.csv`).
- A scratch check (not a report result) ran the S28 alert rule on the "tomorrow = today" forecast. It caught 29 of 43 rises in 2024 with 118 alert runs and 47 of 64 in 2025-26 with 221 runs, against 28 of 43 with 135 runs and 48 of 64 with 238 runs for the ML range. The two error series correlate at 0.999. So the alerts do not depend on the ML model.

The defensible claim is therefore a working alert system plus an honest comparison of how to build one. S36 turns the scratch check into a proper, registered result.

## 3. Step 0: bookkeeping before any code

1. Add rows to `DEVIATIONS.md`: new title and framing; S36, S37, S38 and S39 added; S36 and S38 are post hoc (designed after the S27, S28 and S34 results were seen); the 8 focus items were chosen after results were seen.
2. Point `AGENTS.md` at this file as the current plan.
3. Append S36 to S39 to `state/stages.json` (append only; no old entry changed).
4. Add the settings in section 8 to `config/project.yaml`.
5. Decide what to do with the uncommitted S35 work (`src/stages/s35_rise_5pct.py`, edits to `config/project.yaml`, `src/fpw/prereg.py`, `src/fpw/registry.py`, `state/stages.json`). Ask the user: finish and commit it, or leave it out of the report.

## 4. S36: alert-rule comparison

**Question:** which rule should raise the alerts, and does the ML model add anything to them?

**Rules compared** (all use the same persistence: above the bound on 3 of the last 5 report days, 7-report horizon):

| Rule | Bound |
|---|---|
| A. ML range | as in S28: 95th percentile of the last 120 ML forecast errors per item. Read from `outputs/28_alerts/forecasts_daily.parquet`; nothing refitted |
| B. Simple range | same construction on the "tomorrow = today" forecast, so the error is the 7-report log price change |
| C. Fixed threshold | 7-report rise above a single percentage for all items |

**Fixing the settings (2024 only, before scoring):**

- Rule B's level is chosen from the same candidates as S28 (0.9, 0.95, 0.975, 0.99) by the same procedure: the lowest level with at most 2 false alarms per item-year in 2024 outside the event windows (`fpw.alerts.choose_level`).
- Rule C's threshold is chosen from 3, 5, 7 and 10 % by the same false-alarm target.
- Rule A is not changed.
- The chosen settings are written to `state/prereg_S36.yaml`, committed, and only then is anything scored. Use the same stop-and-commit pattern as S28 and S34.

**Scoring:** the S34 rise reference and matching, unchanged (`fpw.rises`, `config/project.yaml` `rises`). For each rule and period: episodes, detected, recall, alert runs, precision, F1, median delay, alert runs per item-year, placebo mean recall and p-value. Also the overlap between rules A and B (rises caught by both, by one only, by neither). 2024 is validation; 2025-26 is retrospective.

**Outputs:** `reports/project/tables/P11_rule_comparison.csv`, `P11_rule_overlap.csv`, `P11_rule_settings.csv`; a section in `reports/project/RESULTS_REGISTER.md`.

**Check that the scoring is right:** rule A must reproduce `P10_alerts_vs_rises.csv` exactly (28 of 43 with 135 runs; 48 of 64 with 238 runs). The stage fails if it does not.

**Must be stated in the report:**

- Rule C is close to the definition of the rise it is scored against (a 10 % rise over 14 report days), so its score is partly circular. It is a reference point, not the winner.
- The comparison was designed after the alert results were seen.
- Whatever the result, it is reported. If B matches A, the report says the alerts do not need the ML model.

**Where it runs:** light (no model fit). Work PC, reading the Drive copy of `forecasts_daily.parquet` and `features_v2.parquet`.

## 5. S37: price behaviour study

**Purpose:** a descriptive data chapter that explains why the simple baseline is hard to beat. No model, no test seal.

Tables, all from the panel (`tcb_v2_rebuilt.parquet`), 54 modelled items:

| Table | Content |
|---|---|
| `P12_change_frequency.csv` | share of report days on which the price changed, by item and by year |
| `P12_change_size.csv` | median and 95th percentile of the absolute change on days it changed, in Tk and in percent, by item |
| `P12_unchanged_runs.csv` | mean and longest run of unchanged report days, by item |
| `P12_price_step.csv` | smallest price step by item (TCB reports whole taka for minimum and maximum, so the midpoint moves in steps of Tk 0.5) |
| `P12_rise_episodes_by_item.csv` | sustained 10 % rise episodes per item and year, from the S34 rule |
| `P12_ramadan.csv` | median 14-report change in the 30 days before Ramadan against the rest of the year, by item group; descriptive only, no causal wording |

Figures: change frequency by year for the focus items; price series with alert marks for two or three focus items.

Rules: the 2022 gap is never bridged; a blank or zero price is "not reported", never a zero change. No price values in git: tables carry rates and summaries only, as in P2.

Optional, only if time allows: redo the comparison with World Food Programme prices properly (one market, one series per commodity, monthly mean of TCB against the WFP value). The first attempt mixed several markets and is not usable.

## 6. S38: focus-item tables

Eight items, chosen for how often their prices move and for being everyday purchases: Chicken - Broiler, Onion - Local, Egg - Farm, Potato, Soybean Oil - Loose, Palm Oil - Loose, Garlic - Imported, Sugar.

The model is not retrained. The stage subsets existing results:

- `P13_focus_accuracy.csv`: per item and horizon, model error, baseline error, their ratio, accuracy (1 - MAPE), from `P7_accuracy_by_item.csv`.
- `P13_focus_alerts.csv`: per item and period, rise episodes, detected, alert runs, for each S36 rule.
- `P13_focus_ranges.csv`: upper-bound and two-sided coverage per item.

All-item results stay the headline. The report says the eight were chosen after the results were seen, and that soybean oil, palm oil and sugar had no sustained 10 % rise in 2024 to 2026, so their alerts cannot be judged.

## 7. S39: report and docs

New folder `reports/thesis/report_v5/`. Earlier report folders are kept.

| Chapter | Content | Tables |
|---|---|---|
| 1. Introduction | food price rises in Dhaka; daily TCB sheets are read by hand; aim: flag sustained abnormal rises | |
| 2. Background | retail price persistence; machine learning for food prices; ranges and alert rules | |
| 3. Data | TCB sheets, conversion, audit, the 2022 gap, item groups, driver sources and availability dates | P2, P3 |
| 4. Price behaviour | how often and how much prices move; regimes by year; rise episodes | P12 |
| 5. Method | forecast candidates, validation on 2024, ranges, the three alert rules, the rise reference, the sealed test | |
| 6. Results | forecast benchmark; range quality; alert-rule comparison; alerts against news events; driver breakdown; focus items | P5, P7, P8, P9, P10, P11, P13 |
| 7. Discussion | why persistence wins; which alert rule to use; what the breakdown can and cannot say | |
| 8. Limitations | see the list below | |
| 9. Conclusion | a usable monitor, an honest benchmark, next steps | |

**Claims the report makes**

- A daily price dataset built from 1,435 TCB files, with no mismatch in 3,060 audited price cells.
- Six forecast models compared fairly; none beat "tomorrow = today".
- Ranges that hold about 94 % of prices against a 95 % target.
- Alerts that catch 65 to 75 % of sustained 10 % rises, about three times what random dates catch.
- A tested comparison of three alert rules (S36).

**Claims the report does not make**

- That the ML model predicts prices better than the baseline.
- That high accuracy shows the model is good (the baseline has the same accuracy; every accuracy figure sits beside the baseline's).
- Early warning (alerts start about 2 report days after onset).
- That alerts are precise.
- That news-dated shocks are detected better than chance.
- That drivers cause rises, or that the breakdown is stable.
- Novelty beyond "we did not find a study that combines these steps".

**Wording** stays as in `AGENTS.md`: "not explained by measured cost drivers"; never "hoarding", "syndicate", "collusion", "cartel", "manipulation"; "abnormal-rise detection", not "early warning". The range is "a range from recent forecast errors"; do not call it conformal prediction unless the student can defend the term.

**Literature:** no paper is cited from a search summary. Each one is read by the student first. Candidates found on 2026-11-16, unverified: a Bangladesh daily price benchmark (arXiv 2604.06227), a Kenya food price study (Frontiers in AI, 2025), a Uganda study (Springer, 2024), Cavallo's "Scraped Data and Sticky Prices", Klenow and Malin's survey of price setting. Author names and figures must be taken from the papers themselves.

**Also update:** `README.md`, `docs/HOW_IT_WORKS.md`, the dashboard title and captions, `SPEC.md` acceptance checks for S36 to S39.

## 8. Settings to add to `config/project.yaml`

```yaml
# ---- alert-rule comparison (S36). Post hoc: designed after the S28 and S34 results were seen.
alert_rules:
  simple_range: {levels: [0.9, 0.95, 0.975, 0.99]}     # same candidates and choice rule as S28
  fixed_threshold: {candidates: [0.03, 0.05, 0.07, 0.10]}
  fa_target_per_item_year: 2.0                         # same target as alerts.fa_target_per_item_year
  placebo_draws: 300

# ---- price behaviour study (S37)
behaviour:
  ramadan_window_days: 30
  change_window_reports: 14

# ---- focus items (S38). Chosen 2026-11-16 after results were seen; reported as such.
focus_items:
  - Chicken - Broiler
  - Onion - Local
  - Egg - Farm
  - Potato
  - Soybean Oil - Loose
  - Palm Oil - Loose
  - Garlic - Imported
  - Sugar
```

## 9. Order of work

1. Step 0 (section 3). Stop and get the user's OK on the DEVIATIONS rows.
2. S36 phase A: choose rule B and C settings on 2024, write and commit `state/prereg_S36.yaml`.
3. S36 phase B: score, write P11, register. Stop and report.
4. S38: focus tables. Stop and report.
5. S37: behaviour tables and figures. Stop and report.
6. S39: report, docs, dashboard text.
7. `make check`, PROGRESS.md entry, commit and push after each stage.

If time is short, drop in this order: the optional WFP comparison, the Ramadan table, then the S37 figures. S36 is not dropped.

## 10. Data location

Code comes from the repo; data and outputs live in Drive `MyDrive/FoodPriceWatch` and are never committed. For work-PC stages, a Drive download must sit in a durable folder outside git with `FPW_ARTIFACT_ROOT` pointing at it. The copy used on 2026-11-16 was in a temporary session folder and may be gone; the zip `FoodPriceWatch-20261116T141522Z-1-001.zip` in the checkout root is the source.

## 11. Open questions for the user

1. Does the supervisor accept a project in which ML is a compared variant and not the core? Ask before the report is written.
2. Does the title change need approval from the department?
3. Author name: still TO_CONFIRM in `config.yaml`.
4. S35: finish and commit, or leave out?
5. The pending rows in `DEVIATIONS.md` (audit method, register location, onion export coverage gap, stale weather and exchange-rate files) still need a yes or no.
