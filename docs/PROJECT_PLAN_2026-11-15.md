# Bangladesh Food Price Watch: project plan (combined, 15 Nov 2026)

This file combines every decision and change agreed in the planning discussion of 14-15 Nov 2026.
It is the input for re-planning in Claude Code. Where it conflicts with SPEC.md, AGENTS.md or
DECISIONS.md, this file is newer: log each conflict in DEVIATIONS.md before acting on it.

---

## 0. Instructions for Claude Code

1. Enter plan mode. Read this file, then README.md, SPEC.md, AGENTS.md, DECISIONS.md,
   DEVIATIONS.md, docs/ARCHITECTURE.md and docs/DATA_COLLECTION.md.
2. Produce a revised plan: which files you keep, change and add for each step in section 9,
   with the acceptance check for each step. Flag anything here that the code makes impossible
   or that contradicts itself.
3. Ask the open questions in section 11 before starting the step that needs each answer.
4. Build one step at a time. Stop after each step, show what changed, and wait for OK.
5. Update AGENTS.md and SPEC.md to match this plan as part of the first build step (logged in
   DEVIATIONS.md), so later sessions do not follow the old rules.

---

## 1. What the project is

- **A master's PROJECT, not a thesis.** It must read as a prediction system, not a comparative
  or evaluation study, so the supervisor signs it as a project. Comparisons appear only as a
  validation step and in limitations.
- **Objective (one, replacing RQ1-RQ5):** for each TCB item, forecast the price 1, 7, 14 and 30
  report days ahead with an expected range, raise an alert when the price stays above the range,
  and attach a driver breakdown to each alert.
- **Deliverables:** forecasts with ranges, an alert list, a driver breakdown per alert, a small
  Streamlit dashboard, an update script, and plain-English docs. The student writes the report
  later (Overleaf project `fpw_report_overleaf`) from reports/ and reports/RESULTS_REGISTER.md.
- **The student must be able to explain every step** (data, features, model internals,
  training, validation, accuracy, visualisations). Keep methods explainable; prefer one model
  over many.
- People: supervisor and exam-committee chairman is Dr. Mahmudul Hasan, Associate Professor.
  config.yaml `author` stays TO_CONFIRM (see section 11).

## 2. Environment and repository

- Repo: `github.com/mrchowdhury587/foodprice_watch` (transferred from `mehediparvez/foodprice_watch`;
  the README badge and notebook cell 2 still point to the old repo, so update them).
- Runs in Google Colab under the `mehedi11908015` Google account, data and outputs on Google Drive
  (`MyDrive/FoodPriceWatch/`), code cloned from GitHub. Every unit of work stays resumable
  (atomic writes + `_SUCCESS.json` markers). User has a Google One plan; check whether it
  includes Colab Pro before relying on faster machines.
- **Push access:** the cloud session could not push (Claude GitHub App not installed on
  `mrchowdhury587`). Step 1 exists as commit `d8f67f0` / `step1_data_collection.patch`; make sure
  it is in the repo before building on it.
- **Do not edit config.yaml.** Its hash is stored in the S05 unit markers; editing it forces the
  ~2-hour classical-baseline rerun. New settings go in a new `config/project.yaml`.

## 3. Current state

### Old pipeline (stages S00-S11, run 11 Nov 2026 on Colab)
Results are in reports/tables and reports/figures. Key numbers (2025-26 test, 54 long-history series):
- LightGBM vs "tomorrow = today" (gmean relMAE; 1.00 = tie): core 1.00 / 1.02 / 1.03 / 1.08,
  with forecasting drivers (M1) 1.00 / 1.02 / 1.02 / 1.07 at h = 1 / 7 / 14 / 30. Best classical
  model AutoETS 1.18 / 1.05 / 1.04 / 1.03. No model beats naive overall.
- Driver groups: none significantly better than the core model on any item after Holm correction.
  World prices made h=7 about 0.03 worse. Weather improved h=14/30 for 4 vegetables vs placebo
  (gap -0.05 / -0.12).
- Alerts: conformal 97.5% upper bound, 3-of-5 rule, threshold chosen on 2024: 7 of 12 shocks
  detected, 1.83 false alarms per item-year; random placebo dates reach 0.48 recall (p = 0.29).
  Upper-95% coverage 0.92 (Kupiec rejects).
- Explanation: in 13 real rises, the share not explained by measured cost drivers is about 0.65+.
  India's Dec 2023 onion ban: forecasting drivers explain about 35% of the onion rise.
- S02 (audit) blocked without the original TCB Excel files; S03/S08 (WFP) no code; Chronos-2 not run.
- Draft report: reports/thesis/main.tex (thesis framing; to be reframed later, not by the agent
  unless asked).

### Step 1 of the new plan: DONE (commit d8f67f0)
- `tools/tcb_convert.py` added (user's converter). Re-translating Product_Bangla/Unit_Bangla of all
  76,440 rows reproduces Product and Unit exactly.
- `tools/tcb_append.py`: drops the converter's 5 extra columns; `--after-last-base-date` keeps only
  days after the base file's last date (protects the 4 hand corrections). Tested: base cut at
  2026-09-30 plus the full file in converter layout rebuilt the original exactly.
- `docs/DATA_COLLECTION.md`: download -> convert -> append, with checks.
- Waiting for: the user's new TCB reports (or the zipped `Downloads/TCB_Daily_RMP` folder, which
  would also unblock the audit).

## 4. Data

### Collection
| Source | Use | Collected by |
|---|---|---|
| TCB daily retail price reports (Bangla Excel, tcb.gov.bd) | Target: daily Dhaka retail prices, 63 series, 17 May 2021 - 24 Oct 2026, to be extended to the latest report | User runs `tools/tcb_download.py`; agent never downloads from TCB |
| Open-Meteo weather, 13 locations | Weather driver (+5 day publication lag) | Existing file |
| BDT per USD (npm market series from 2024-03-02, Yahoo x 1.0151 before) | Exchange-rate driver | Existing files |
| `exporter_policy_events.csv` | India onion export measures | Existing file (India onion ban dates verified against DGFT) |
| `bd_ramadan_eid.csv`, `bd_public_holidays_2019_2027.csv` | Calendar | Existing files |
| `shock_events.csv` (12 in-window episodes from 22 news-documented ones) | Alert evaluation and case studies only | Existing; no new labelling |
| Original TCB Excel files | Data audit (2% sample: 28 days, 1,530 values; 5 ginger candidates) | Requested from user |

### Not used, and why
- databd.online library: reviewed all 43 datasets; nothing adds to the project (WFP, rainfall,
  cyclones and trade duplicate existing files; the rest is unrelated). IMF PortWatch daily port
  calls is the only new signal; skipped to avoid complexity (future work).
- `tcb_combine_english.py`: older converter, names do not match the price file.
- `ifpri_export_restrictions.py`: the IFPRI sheet is dead.
- `pipeline.py`, `data.py`, `harness.py`: earlier versions of current code; pipeline.py uses a
  75-day import lag that leaks future data.
- WFP market prices: kept only as an optional cross-check of TCB (rice, lentil, soybean oil); the
  "national vs local" question (RQ5/S08) is out of scope.

### Preprocessing rules (unchanged, each has a test)
- Time index = report days (`report_idx`), not calendar days.
- Blank or zero price = not reported; never imputed in targets. Inputs may carry the last
  reported price forward.
- The sparse 2022 period (12 Mar - 31 Dec 2022, 24 reports) is history only, never scored.
- No outlier removal: real jumps are what the alerts must catch; suspicious values are flagged
  for the audit.
- Short-history items (9 series) are scored and reported separately.
- Every driver joins on its true publication date; missing drivers stay empty with a has_ flag.
- Never edit data/raw/. The extended price file arrives under a new name
  (e.g. `tcb_dhaka_daily_prices_2021_2026_v2.csv`); intake (S00) and S01 must accept it, and the
  longer sample is logged in DEVIATIONS.md.

## 5. Features

| Group | Features | Notes |
|---|---|---|
| Price history | log change over the last 1, 7, 14, 30 reports; deviation from 30-report mean; 30-report volatility; reports since last price change | **Windows configurable** in `config/project.yaml` (e.g. `lags: [1, 7, 14, 30]`, `rolling: [30]`); chosen on validation data only |
| Item identity | `item_code`, `stratum_code` as LightGBM categorical features | Integer codes treated as categories; no one-hot |
| Calendar (known ahead) | month, weekday, days to Ramadan / Eid ul-Fitr / Eid ul-Adha, in Ramadan, holidays in next 7 days, days since previous report | Lets the model anticipate dated events |
| Weather | 3 features chosen on 2024 (current: 7-day max temperature, 30-day mean temperature, 7-day rain) | Vegetables, potato, onion, garlic, ginger |
| India onion export measures | active measure flag | Local and imported onion |
| Exchange rate | log BDT/USD level and 30-day change | Imported, administered and spice items; moves from explanation-only to a model input |
| Horizon | `horizon` = 1, 7, 14, 30 | Lets one model serve all horizons |

**Drivers removed** (evidence from the old run; the student asked to cut drivers that do not help):
world prices (IMF; made h=7 worse, wrong-sign SHAP at h=7/14), Brent oil (near-zero SHAP, no effect),
fishing bans (one item, zero SHAP), diesel (few changes, tiny SHAP), Comtrade imports (208-day lag,
small SHAP; also removes the 208-day leakage test), event flags (partial coverage Oct 2023 - Nov 2025,
many reconstructed dates), sugar/chickpea world prices (2 items, unstable sign). Unused raw files:
remittances, reserves, CNY/INR/MYR, WTI, FAO index. Kept drivers are modest: none passed a per-item
significance test, so describe them as helpful for specific items, not proven.

No feature scaling (trees are scale-free; logs make items comparable), no polynomial/interaction terms
(trees find interactions), no PCA/t-SNE (about 25 features, and PCA would make them unexplainable).

## 6. Model

- **Paradigm:** supervised regression on tabular data (machine learning, not deep learning, as the
  main model). The future price is the label, available from history.
- **Main model: ONE LightGBM** for all items and all horizons. Each training row is stacked four
  times with `horizon` = 1, 7, 14, 30; target = log price change from the forecast date to that
  horizon; L1 (MAE) objective. Forecast = today's price x exp(predicted change). Not a recursive
  1-step model (errors would compound and it would need future driver values).
- **Model selection step (new):** candidates evaluated on the validation period with the same
  features where applicable, winner chosen on validation only, then only the winner tested on
  2025-26. Presented as "candidates evaluated, model chosen", not as research questions.

| Candidate | Type | Purpose |
|---|---|---|
| Naive ("tomorrow = today") | baseline | reference |
| ETS | classical | own past only (already run in S05) |
| Ridge regression | linear, same features | are trees needed? |
| Random Forest | trees | alternative ensemble |
| LightGBM | boosted trees | current choice |
| LSTM | deep learning (sequence) | examiners often ask |
| ETS + LightGBM hybrid | hybrid | LightGBM corrects ETS errors |
| Chronos-2 (optional) | pretrained foundation model | zero-shot; needs Colab GPU |

  Final candidate list is an open question (section 11).

- **Tuning:** Optuna, fixed budget of about 50 trials, searching tree size (4-63 leaves), learning
  rate (0.01-0.1), number of trees with early stopping, minimum rows per leaf, feature and row
  sampling shares, L1/L2 penalties, and the loss (MAE, Huber, squared error). Tune on Jan-Sep 2024,
  confirm on Oct-Dec 2024; if the winner loses its edge there, keep the simpler setting. Report all
  trials in an appendix table. Reason for widening: the old 4-setting grid's best (15 leaves,
  150 trees, mean 1.067) sat at the edge of the grid; larger settings were worse.
- **Why 2024 for selection:** the only full calendar year with enough training data before it
  (2021 from May, sparse 2022, full 2023), covering all seasons, and not overlapping the test.
  Option: Jul 2023 - Dec 2024 (open question).
- **Production model:** retrained on all data up to the latest report after validation; saved to
  `models/`.
- **Compute (estimated from old runs, about 2 s per fit on 2 CPUs):** one setting on 2024 under
  1 minute; 50 trials 30-60 minutes; 500 trials several hours; final test 10-20 minutes; classical
  models about 2 hours; LSTM about an hour on CPU.

## 7. Evaluation

Fix this list in the pre-registration file before the test is run; MAE is the primary metric;
report every number, including unflattering ones.

- **Accuracy:** MAE (Tk, primary), RMSE, MAPE, MASE, error relative to "tomorrow = today", bias
  (mean signed error), direction accuracy on days the price moved, error on change days vs
  unchanged days (prices are unchanged on 85-93% of days, so averages hide where the model
  matters), R2 on price changes (not levels).
- **Validation schemes:** rolling origin with expanding window on 2025-26 (main, 87 forecast
  dates); year-by-year walk-forward (test 2023, 2024 [label as tuning year], 2025-26) for
  stability; sliding 500-report window as a check. No random or stratified k-fold (leaks the future).
- **Error analysis:** by item group, item, horizon, month (Ramadan/Eid vs normal), rising vs
  falling periods, before/after mid-2024; actual-vs-forecast plots for key items; error
  distribution; bias over time; worst-20 forecasts table; learning curve (train vs validation
  error by number of trees); Diebold-Mariano vs naive as supporting evidence.
- **Range:** coverage of the upper bound, average width, pinball loss, Winkler score, by item group
  and horizon.
- **Alerts:** event-level counts (shocks caught, missed, alerts outside windows; no true negatives,
  so no accuracy/specificity), recall, precision, false alarms per item-year, lead days before the
  news peak, precision-recall curve, random-date placebo.
- **Explanations:** SHAP sign checks (weaker taka -> higher imported prices), stability of top
  drivers across refits, case studies.
- The 2025-26 period was already scored by the old model, so the new model's test is not a first
  look; tuning stays on 2024 only. State this in limitations.

## 8. Alerts and explanation

- **What the alert is:** abnormal-rise DETECTION, not early warning. Each report day, compare the
  actual price with the forecast made 7 reports earlier. Upper bound = per-item conformal 97.5%
  quantile of that item's last 120 forecast errors. Alert starts when the price is above the bound
  on 3 of the last 5 reports.
- **Threshold** fixed on 2024 non-event periods (target: at most 2 false alarms per item-year),
  never tuned on the 12 shocks.
- **The model is not trained on events.** The alert is a rule on top of a normal-price forecast.
  The 12 shock episodes are used only after the fact: (a) did an alert start inside each event's
  window (14 days before onset to 30 days after news peak)? (b) how much of each rise did the
  drivers explain? With 12 events, recall 7/12 has a 95% range of about 32-81%: state as a
  limitation. Option to add events later: agent drafts from news with sources, user verifies
  (3-5 min per row); not planned now.
- **Range per horizon:** conformal bounds for 1, 7, 14 and 30 so the dashboard shows a range for
  each forecast.
- **Explanation:** SHAP at four levels: overall, by item group, per item, per forecast/alert, grouped
  as price history, calendar, weather, onion export measures, exchange rate. The part of a rise above
  the bound is "not explained by measured cost drivers".
- **Early warning (forecast X% above today, or a yes/no "rise > 10% in 14 reports" model):** future
  work; evidence so far suggests rises are hard to predict in advance.

## 9. Build order

| Step | What | Acceptance check |
|---|---|---|
| 1 | Data collection tools | DONE (commit d8f67f0) |
| 2 | Intake + panel on the extended price file (S00, S01); accept the new filename; log the longer sample; run the audit if originals arrive | rows, series, dates reported; S01 invariants pass; audit error rate with 95% CI or "not measured" |
| 3 | Features: trim S04 to the kept drivers; exchange rate as model input; configurable windows in config/project.yaml | leakage tests (weather +5 d, world-price test removed with the driver) and no-inf test pass |
| 4 | Single-model code in src/fpw/ml.py (horizon stacking) | unit test: one model predicts all four horizons; no target uses a missing or gap-period price |
| 5 | Model selection on validation (candidates in section 6) | one table of validation scores; winner recorded before the test |
| 6 | Optuna tuning of the winner (if LightGBM) on Jan-Sep 2024, confirm Oct-Dec 2024 | all trials saved; chosen setting written to the pre-registration |
| 7 | Pre-register, commit, test once on 2025-26; full evaluation (section 7) | seal file; evaluation tables and figures; RESULTS_REGISTER entries |
| 8 | Ranges and alerts (section 8) | coverage, recall, false alarms reported; threshold from 2024 |
| 9 | Explanation (SHAP four levels) | sign checks; per-alert breakdown |
| 10 | Train production model on all data; export forecasts.parquet, alerts.csv, alert_drivers.csv | files exist with the documented columns |
| 11 | Streamlit dashboard: pick item and horizon; history, forecast with range, alerts, drivers, driver importance | runs locally / in Colab from the three files; no login, no database |
| 12 | `tools/update.py`: longer price CSV -> re-run steps 2-10 | end-to-end run on the extended file |
| 13 | Docs: README around the objective; docs/HOW_IT_WORKS.md (each step, why, why this method); move old comparison tables to reports/validation/ labelled "earlier design" | review by the user |

## 10. Rules

- Never edit data/raw/; never impute target prices; never score the 2022 gap; never remove real jumps.
- Never use a driver value before its publication date.
- Wording: residual rises are "not explained by measured cost drivers". Never hoarding, syndicate,
  collusion, manipulation or cartel.
- Every reported number comes from a committed script and is listed in reports/RESULTS_REGISTER.md.
- Choose models, settings, windows and thresholds on validation data only; test once. If the model
  does not beat "tomorrow = today", say so in limitations; never tune on the test.
- Do not edit config.yaml; new settings in config/project.yaml.
- Do not delete or reorder entries in state/stages.json; add new stages for the new steps.
- Log every change from SPEC.md in DEVIATIONS.md before continuing. Replace the AGENTS.md rule
  "driver groups are added one at a time" (it describes the dropped comparison study).
- Ask before anything destructive or externally visible (force-push, publishing, public dashboard).

## 11. Open questions for the user

1. Model-selection candidates: all eight in section 6, or a shorter set (naive, ETS, Ridge,
   Random Forest, LightGBM, LSTM)? Include Chronos-2?
2. Validation period: 2024 (Jan-Sep tune, Oct-Dec confirm) or Jul 2023 - Dec 2024?
3. Is the dashboard required by the supervisor, or optional?
4. Push access: install the Claude GitHub App on `mrchowdhury587`, or keep applying patches?
5. New TCB data: will the user send the zipped Excel folder (agent converts and audits) or the
   appended CSV?
6. Author name for config.yaml (student Romjan Chowdhury per DECISIONS D2 update) — set only when
   the run is next re-done, since config.yaml is hashed.

## 12. Known limitations to carry into the report

- Prices are sticky; no model clearly beats "tomorrow = today" overall.
- Kept drivers help only specific items; none significant per item.
- Alerts are detection, not early warning; evaluated on 12 events only; placebo recall is close.
- 2025-26 test period was seen by the earlier model.
- TCB covers Dhaka markets only; prices are min-max ranges across markets and qualities.
- Data transcription accuracy is unmeasured until the audit runs.
