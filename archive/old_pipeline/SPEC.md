# SPEC.md — Bangladesh Food Price Watch (project, not thesis)

Revised 2026-11-15 from docs/PROJECT_PLAN_2026-11-15.md. Every change from the earlier text is logged in DEVIATIONS.md. Part A is the current scope. Part B is the earlier design (stages S00-S11, run 2026-11-11); its results are kept as validation material and are not extended.

# Part A — Prediction system (stages S22-S33)

## Goal
One objective: for each TCB item, forecast the Dhaka retail price 1, 7, 14 and 30 report days ahead with an expected range, raise an alert when the price stays above the range, and attach a driver breakdown to each alert. Deliverables: forecasts with ranges, an alert list, a driver breakdown per alert, a small Streamlit dashboard, an update script, and plain-English docs. The author writes the report later from reports/ and reports/RESULTS_REGISTER.md. The project must read as a prediction system, not a comparative study: comparisons appear only as a validation step and in limitations. The student must be able to explain every step, so methods stay explainable and one model is preferred over many.

## Out of scope
National-vs-local labelling with WFP prices (old RQ5/S08), driver-group significance testing as a research question (old RQ2), ALPS/IFPA alert baselines, early warning (forecast X% above today, or a yes/no rise model), new event labelling, IMF PortWatch, a public dashboard, papers, Zenodo. Deep learning appears only as a model-selection candidate if DECISIONS.md enables it.

## Data
- Target: TCB daily retail prices, 63 series, from 2021-05-17 to the latest report. The extended file arrives under a new name (config/project.yaml `price_file`); data/raw/ is never edited.
- Kept drivers: calendar (known ahead), weather (3 features chosen on 2024; vegetables, potato, onion, garlic, ginger), India onion export measures (onions), exchange rate (imported, administered and spice items).
- Removed drivers (evidence from the earlier run): IMF world prices, Brent, fishing bans, diesel, Comtrade imports, event flags, sugar/chickpea world prices. Unused raw files: remittances, reserves, CNY/INR/MYR, WTI, FAO index.
- shock_events.csv (12 in-window episodes) is used only to evaluate alerts and for case studies. The model is never trained on events.

## Preprocessing rules (each has a test)
1 time index = report days · 2 blank or zero price = not reported; never imputed in targets; inputs may carry the last reported price forward · 3 gap_2022 (2022-03-12..2022-12-31, 24 reports) is history only, never scored · 4 no outlier removal; suspicious values are flagged for the audit · 5 short-history items (9 series) are scored and reported separately · 6 every driver joins on its true publication date (weather + 5 d; exchange rate as of the last value on or before the report date; carry cap 7 d); missing drivers stay empty with a has_ flag · 7 no ±inf · 8 the extended panel equals the earlier panel on every date up to 2026-10-24 and keeps the same report index there.
The data rules of Part B (1-34) still apply to the files they concern.

## Features and model
- Features: log change over the last 1, 7, 14, 30 reports; deviation from the 30-report mean; 30-report volatility; reports since last price change (windows set in config/project.yaml, chosen on validation data only); item and stratum codes as LightGBM categories; calendar; weather; onion export measure flag; log BDT/USD level and 30-day change; `horizon`. No scaling, no polynomial terms, no PCA.
- Main model: ONE LightGBM for all items and horizons. Each row is stacked four times with horizon = 1, 7, 14, 30; target = log price change from the forecast date to that horizon; forecast = today's price × exp(predicted change). Not recursive.
- Model selection: candidates (DECISIONS.md) are scored on the validation period with the same features where applicable; the winner is chosen on validation only; only the winner is tested.
- Tuning: Optuna, about 50 trials, on Jan-Sep 2024, confirmed on Oct-Dec 2024; if the winner loses its edge there, the simpler setting is kept; all trials are reported.
- Production model: retrained on all data up to the latest report, saved to models/ (not in git).

## Evaluation protocol (fixed in state/prereg_S27.yaml before the test)
- Split: validation = 2024 (models, settings, windows, weather choice, alert threshold). Test = 2025-01-01..2026-10-24, the same 87 forecast origins as the earlier run, expanding window, unsealed once. The earlier model already scored this period, so it is not a first look: stated in limitations.
- Accuracy: MAE in Tk (primary), RMSE, MAPE, MASE, error relative to "tomorrow = today", bias, direction accuracy on days the price moved, error on change days vs unchanged days, R² on price changes.
- Schemes: rolling origin on 2025-26 (main); year-by-year walk-forward (2023, 2024 labelled tuning year, 2025-26); sliding 500-report window. No random or stratified k-fold.
- Error analysis: by item group, item, horizon, month (Ramadan/Eid vs normal), rising vs falling periods, before/after mid-2024; actual-vs-forecast plots; error distribution; bias over time; worst-20 table; learning curve; Diebold-Mariano vs naive as supporting evidence.
- Range: coverage of the upper bound, average width, pinball loss, Winkler score, by item group and horizon.
- Alerts: abnormal-rise detection. Each report day the actual price is compared with the forecast made 7 reports earlier; upper bound = per-item conformal quantile of that item's last 120 forecast errors; an alert starts when the price is above the bound on 3 of the last 5 reports. The level is fixed on 2024 non-event periods (at most 2 false alarms per item-year), never on the 12 shocks. Reported: shocks caught and missed, alerts outside windows, recall, precision, false alarms per item-year, lead days before the news peak, precision-recall curve, random-date placebo. Event window: 14 days before onset to 30 days after the news peak.
- Explanation: SHAP at four levels (overall, item group, item, forecast/alert), grouped as price history, calendar, weather, onion export measures, exchange rate; sign checks; stability of top drivers across refits; case studies. The part of a rise above the bound is "not explained by measured cost drivers".

## Stages and acceptance criteria
S22 Intake + panel on the extended price file; audit — rows, series and dates reported; S01 invariants pass; panel equals the earlier panel up to 2026-10-24; audit error rate with Wilson 95% CI over the 1,530 sampled values and a decision per ginger candidate, or "not measured".
S23 Features — kept drivers only; exchange rate as a model input; windows from config/project.yaml; leakage tests (weather + 5 d, exchange rate as-of) and the no-inf test pass; kept columns equal the earlier feature table up to 2026-10-24.
S24 Single-model code — unit test: one model predicts all four horizons; no target uses a missing or gap-period price; no training target lies after the cutoff.
S25 Model selection — one table of validation scores; winner and rule recorded and committed before the test.
S26 Tuning — all trials saved; chosen setting written to the pre-registration.
S27 Pre-register, commit, test once; full evaluation — seal file with one unsealing; evaluation tables and figures; RESULTS_REGISTER entries.
S28 Ranges and alerts — coverage, recall, false alarms reported; threshold from 2024.
S29 Explanation — sign checks; per-alert breakdown; wording test passes.
S30 Production model + exports — forecasts.parquet, alerts.csv, alert_drivers.csv exist with the documented columns.
S31 Dashboard — pick item and horizon; history, forecast with range, alerts, drivers, driver importance; runs from the three files; no login, no database.
S32 Update script — a longer price CSV re-runs intake, panel, features, alert log, per-alert drivers, production fit and exports end to end. Selection, tuning and the sealed test are not re-run.
S33 Docs — README around the objective; docs/HOW_IT_WORKS.md; earlier comparison tables copied to reports/validation/ labelled "earlier design"; reviewed by the user.

## Known limitations to carry into the report
Prices are sticky and no model clearly beats "tomorrow = today" overall · kept drivers help only specific items, none significant per item · alerts are detection, not early warning, evaluated on 12 events only, with placebo recall close · the 2025-26 test period was seen by the earlier model · TCB covers Dhaka markets only and prices are min-max ranges across markets and qualities · transcription accuracy is unmeasured until the audit runs.

# Part B — Earlier design (stages S00-S11; kept, not extended)

## Goal
Detect, locate and explain unexplained food price rises in Bangladesh. Forecast Dhaka TCB daily retail prices h = 1, 7, 14, 30 report days ahead; test whether external drivers add value beyond persistence, and for which goods; raise alerts when a price leaves its expected range; label flagged rises national/regional/local with WFP monthly market prices; decompose rises into "explained by measured cost drivers" and "not explained by measured cost drivers". Output: a reproducible repo and a results pack (reports/). The author writes the report later.

## Research questions
RQ1 Benchmark: on the 54 long-history series, does any model (Naive, SeasonalNaive, WindowAverage, RWD, AutoARIMA, AutoETS, AutoTheta, LightGBM, Chronos-2) beat naive, per eval_stratum and horizon?
RQ2 Driver value: starting from a core model (price + G0 calendar), does adding each driver group G1..G5 (one at a time, pre-registered order, mapped items only) improve over core and over naive, and does the matched driver beat a placebo assignment?
RQ3 Alerts: do interval-based alerts flag the 12 in-window shocks (BD-S09, S11, S12, S13, S14, S15, S16, S17, S19, S20, S21, S22) before news_peak, with how many false alarms per item-year, vs ALPS-style and IFPA-style rules?
RQ4 Explanation: for priority-item rises, what share do M0 ⊂ M1 ⊂ M2 explain and what residual remains; event studies for India's Dec 2023 onion ban, 2024-25 FX moves, and the Sep 2023 caps only if DECISIONS D10 supplies dated, sourced cap events.
RQ5 Locate (if WFP supplied): for each item-month flagged in WFP (ALPS-style, real-time trend) or by TCB alerts, what share of non-camp markets is in alert (breadth), and is the rise national, regional or local; do WFP Dhaka markets agree with TCB?

## Out of scope unless DECISIONS.md says otherwise
Dataset or benchmark papers, Zenodo, public dashboard, TimesFM and other extra foundation models, deep learning from scratch, river discharge, DAM wholesale, daily market-level modelling outside Dhaka, ACLED/GloFAS/CPI/hartal sources (optional S14).

## Evaluation protocol (fixed)
- Time index: report days. gap_2022 = 2022-03-12..2022-12-31 is history only; no price is filled across it.
- Split: tuning/validation = calendar 2024 (all hyperparameters, weather-feature choice, G1 series list, carry caps, alert thresholds). Test = Jan 2025 - Oct 2026, the same 87 origins as the existing baseline (S05 recovers them; if impossible, monthly origins in that span, logged). Expanding window. The test is unsealed once per stage (seal file).
- RQ2 tests: per group, DM-HLN of (core + group) vs core on each mapped item, Holm across items within the group, alpha 0.05, pre-registered in state/prereg_S06.yaml. Placebo: the same group assigned to unmapped items drawn with a fixed seed; report the matched-minus-placebo gap with a bootstrap CI.
- RQ3 origins: daily one-step-ahead from config.alert_eval_start (2023-06-01), refit every config.refit_every; thresholds frozen from 2024 non-event periods; report 2025-26 events separately as the clean test.
- Metrics: MAE (Tk), MASE (in-sample one-step naive scaling), gmean relMAE vs naive, win rate; pinball (0.9, 0.95), coverage, Winkler; DM-HLN + Holm; event recall, lead days (report and calendar days), false alarms per item-year, PR curve; Kupiec on non-event periods. Short-history items are scored and reported separately.
- Availability: monthly world prices month end + 40 d; Comtrade month start + 208 d; weather + 5 d; daily FX/Brent as of the last value on or before the report date; carry caps per config. Event matching window [onset - 14 d, news_peak + 30 d].
- RQ5: WFP retail prices only, one unit and currency per item after normalisation; market × item monthly ALPS-style residual with an expanding (real-time) trend + month dummies, alert z >= 1; national median from markets with is_camp_market = 0; breadth = share of reporting non-camp markets in alert; national if breadth >= 0.5, regional if 0.2-0.5 or all alerts in one division, local otherwise (cutoffs pre-registered in prereg_S08.yaml; change only via DECISIONS).

## Data rules (each has a test in tests/)
1 report-day index · 2 gap_2022, no fill across · 3 rebuild item_id and derived columns, output tcb_v1.0_rebuilt · 4 Palm Olein 2 L 2025-04-18 → corrections_proposed.csv; palm olein excluded · 5 two Min-only rows flagged · 6 ginger 2021 reversals flagged · 7 audit needs originals else blocked · 8 item_meta %d-%m-%y · 9 CSV once · 10 normalise pack sizes · 11 respect eval_stratum · 12 missing = not reported · 13 Comtrade blank ≥ 202605, zero-pad HS, never assign 703/910 to one item · 14 IMF parser, PCHANA USD/100 kg · 15 FAO skiprows=1 · 16 weather blocks, coordinate mapping logged, drop last day · 17 FX splice npm from 2024-03-02, Yahoo × 1.0151 before; remittance-implied rate as QA only · 18 keep real jumps; WTI dropped · 19 utf-8-sig · 20 carry confidence · 21 out-of-coverage = unknown · 22 shock join on Product; S15 question · 23 magnitudes are text · 24 import_figures, remittance, reserves context only · 25 Comtrade available = month start + 208 d; leakage test must fail on 75 d · 26 unit value NaN when tonnes = 0; no ±inf · 27 missing driver = empty + has_ flag, never 0 · 28 carry caps · 29 WFP rows dated < 2000 quarantined · 30 camp markets tagged from a user-approved list, excluded from national medians · 31 WFP price type/unit/currency filtered and logged · 32 OHLC day/month order resolved only if unambiguous, else blocked · 33 AgriPriceBD cross-check garlic, chickpea vs TCB and chilli vs WFP; no invented bridge · 34 IMF is the only G1 source; Pink Sheet cross-check only.

## Stages and acceptance criteria
S00 Scaffold + intake — all project files and supplied external files in MANIFEST with sha256; missing ones listed MISSING; config.yaml, item_driver_map.yaml, DECISIONS.md present; `make check` passes; first commit.
S01 Rebuild panel — 76,440 rows; 1,412 dates (2021-05-17..2026-10-24); 63 item_ids equal to item_meta; 0 duplicate (Date, item_id); Avg == (Min+Max)/2 except 2 flagged rows; Min ≤ Max; Week_Ago_Min matches own Min 7 calendar days earlier on ≥ 99.5% of matchable rows; corrections.csv reflected (MS Rod 70,500; Palm Olein 5 L 2025-04-18 missing); corrections_proposed.csv; parquet + sha256; T1, F1, F2.
S02 Audit (human-in-the-loop) — audit sheet from audit_sample_2pct.csv and audit_candidates.csv; if originals supplied and checked: error rate with Wilson 95% CI over 1,530 values and a decision per ginger candidate; else blocked. T2 either way ("not measured" if blocked). Now carried out inside S22.
S03 External intake + cross-checks — each supplied source parsed by a dedicated reader with a unit test. WFP: rows < 2000 quarantined (count reported), price type/unit/currency normalised, camp-market list proposed and approved, TCB↔WFP item crosswalk proposed and approved, measured coverage per item × market. AgriPriceBD: 5 series, measured dates. Pink Sheet vs IMF: level correlation and turning-point agreement on mapped commodities. OHLC: day/month order resolved or blocked; measured first/last dates, markets, items; note on whether it duplicates TCB (novelty check). T3b produced. Missing sources → their parts blocked, the rest proceeds.
S04 Driver panel — one long item × date table on report days with G0..G5 slots and E1..E4 explanation columns per config/item_driver_map.yaml; has_<slot> flags; availability dates and carry caps applied; leakage test passes (shifting any driver one availability step later changes no feature before that step; the 75-day import rule must fail the test); no ±inf; Comtrade 208-day lag confirmed or the value used recorded; weather reduced to ≤ 3 features chosen on 2024 only; G1 series list fixed on 2024; T3.
S05 Reproduce baseline — statsforecast models re-run under recovered settings (training window, refit, origins, season length 7, MASE scaling) written to config; ALL-stratum gmean relMAE within ±0.02 of baseline_results_by_group.csv for every model × horizon, or differences explained; original untouched.
S06 Core benchmark + driver value — prereg_S06.yaml committed before unsealing (core spec, group order G1..G5, mapped items, tests, alpha, placebo seed); 2024 tuning done before unsealing; LightGBM core and core + each group, Chronos-2 price-only (and with covariates if supported, else logged); unit = (model, variant, origin) with marker; test unsealed once; T4, T5, T5b, F3, F4.
S07 Intervals and alerts — conformal (or quantile) intervals with coverage per stratum; prereg_S07.yaml (rules, levels, persistence, operating point from 2024 non-event false alarms) committed before event scoring; ALPS-style and IFPA-style baselines on the same data; all 12 events in T7 including misses and low-confidence ones, tagged test vs in-sample; T6, T8, F5, F6, F7.
S08 Locate (WFP; skipped if D3/D9 say so) — prereg_S08.yaml committed before scoring; unit = (market, item) fit with marker; national median excludes camp markets; breadth labels for every WFP-flagged item-month and every TCB-flagged month with WFP coverage; TCB-vs-WFP Dhaka agreement; T12, F10.
S09 Explanation — M0, M1, M2 per priority item; share explained per episode; SHAP global and per-episode; sign checks (FX, world price); India/Indonesia ban dates verified against cited sources before use, or results marked "reconstructed dates"; wording test passes; T9, T10, F8, F9.
S10 Robustness — weekly vs daily, Min/Max/Avg, sliding vs expanding, placebo event dates (flag rate near nominal), leave-one-event-out, ginger candidates excluded, reconstructed-event rows excluded; T11.
S11 Results pack — clean re-run on a copy reproduces T4, T5, T7, T9 (and T12 if run) exactly with the seed; RESULTS_REGISTER.md lists every number with file, command, commit; reports/README.md indexes tables and figures by RQ.
S12-S14 Optional (dashboard; extra foundation models; data-gap sources: BBS CPI with base-year link factor, BB FX, ACLED, GloFAS, hartal calendar) — only if DECISIONS.md enables them; each new source goes through S03-style intake first.
S99 Review — a fresh reviewer session checks every SPEC line against the repo, pass/fail with evidence.
