# Results register: prediction system (stages S22-S33)

Every number reported for the prediction-system track is listed here with its file, the command that produced it and the code commit.
Numbers of the earlier design (S00-S11) are in `reports/RESULTS_REGISTER.md`, which is not changed. Author: see config.yaml (TO_CONFIRM means no name is used).

## S22 audit of the price file against the original TCB Excel files

Run 2026-11-15 on the work PC, code commit `5a7167f`. Price file: `tcb_dhaka_daily_prices_2021_2026_v2.csv`, sha256 `0159e1f43c5eb95a434fd19033282d7dc3fbca83f48c3650f693b9feed525263`. Originals: `Downloads/TCB_Daily_RMP` (1,435 files).

Command: `python tools/tcb_audit.py --prices tcb_dhaka_daily_prices_2021_2026_v2.csv --sample audit_sample_2pct.csv --candidates audit_candidates.csv --corrections corrections.csv --originals Downloads/TCB_Daily_RMP --out-dir reports/project/tables`

File: `reports/project/tables/P2_audit_summary.csv` (detail per value: `P2_audit.csv`)

| measure | value |
|---|---|
| sampled rows (date x item) | 1530 |
| report days in the sample | 28 |
| rows checked against the original file | 1530 |
| rows not checked (file or row not found) | 0 |
| rows with a mismatch | 0 |
| row error rate | 0.0 |
| row error rate, Wilson 95% low | 0.0 |
| row error rate, Wilson 95% high | 0.0025 |
| price cells checked (Min and Max) | 3060 |
| price cells with a mismatch | 0 |
| cell error rate | 0.0 |
| cell error rate, Wilson 95% low | 0.0 |
| cell error rate, Wilson 95% high | 0.00125 |
| cells that are hand corrections (not errors) | 0 |
| rows where the sheet date could not be confirmed | 0 |
| rows where the CSV differs from the stored sample value | 0 |
| candidate 2021-06-20 Ginger - Local | per kg,"CSV equals the original TCB file: value kept |  stays flagged" |
| candidate 2021-09-15 Ginger - Local | per kg,"CSV equals the original TCB file: value kept |  stays flagged" |
| candidate 2021-09-17 Ginger - Local | per kg,"CSV equals the original TCB file: value kept |  stays flagged" |
| candidate 2021-11-06 Ginger - Local | per kg,"CSV equals the original TCB file: value kept |  stays flagged" |
| candidate 2021-11-27 Ginger - Local | per kg,"CSV equals the original TCB file: value kept |  stays flagged" |

What it measures: agreement between the CSV and the original files (transcription). It is a machine re-read, independent of the converter; it is not a human check and cannot detect a number TCB itself typed wrongly.

## S22 extended price file (work PC; the panel numbers are added after the Colab run)

Run 2026-11-15, code commit `5a7167f`. Commands: `python tools/tcb_convert.py --in Downloads/TCB_Daily_RMP --out-csv converted_all.csv`, then `python tools/tcb_append.py --base tcb_dhaka_daily_prices_2021_2026.csv --new converted_all.csv --out tcb_dhaka_daily_prices_2021_2026_v2.csv --after-last-base-date`

| measure | value |
|---|---|
| original files read | 1,435 (1,430 used, 3 second files for a date already read, 2 not real Excel files) |
| base file | 76,440 rows, 1,412 report days, last 2026-10-24 |
| rows added | 1,080 (18 report days, 2026-10-25 to 2026-11-12, 60 rows each) |
| extended file | 77,520 rows, 1,430 report days, 2021-05-17 to 2026-11-12, 63 series |
| untranslated or auto-translated names in the new days | 0 |

<!-- S27 -->
## S27 sealed test and evaluation (2025-01 to 2026-10, 87 origins)

Run 2026-11-16, code commit `b58aba5`.

Command: `python -m fpw.runner S27`

File(s): `reports/project/tables/P7_accuracy_by_horizon.csv`

| measure | value | file |
|---|---|---|
| h=1: mean absolute error of the log price change | 0.00275 | `P7_accuracy_by_horizon.csv` |
| h=1: error relative to tomorrow = today (geometric mean over items) | 1.01 | `P7_accuracy_by_horizon.csv` |
| h=1: mean absolute error in Tk | 3.114 | `P7_accuracy_by_horizon.csv` |
| h=1: direction accuracy on days the price moved | 0.1451 | `P7_accuracy_by_horizon.csv` |
| h=1: bias in Tk (forecast - actual) | -1.247 | `P7_accuracy_by_horizon.csv` |
| h=7: mean absolute error of the log price change | 0.01203 | `P7_accuracy_by_horizon.csv` |
| h=7: error relative to tomorrow = today (geometric mean over items) | 1.001 | `P7_accuracy_by_horizon.csv` |
| h=7: mean absolute error in Tk | 23.77 | `P7_accuracy_by_horizon.csv` |
| h=7: direction accuracy on days the price moved | 0.1881 | `P7_accuracy_by_horizon.csv` |
| h=7: bias in Tk (forecast - actual) | -4.429 | `P7_accuracy_by_horizon.csv` |
| h=14: mean absolute error of the log price change | 0.01991 | `P7_accuracy_by_horizon.csv` |
| h=14: error relative to tomorrow = today (geometric mean over items) | 1.001 | `P7_accuracy_by_horizon.csv` |
| h=14: mean absolute error in Tk | 43.18 | `P7_accuracy_by_horizon.csv` |
| h=14: direction accuracy on days the price moved | 0.2785 | `P7_accuracy_by_horizon.csv` |
| h=14: bias in Tk (forecast - actual) | -6.031 | `P7_accuracy_by_horizon.csv` |
| h=30: mean absolute error of the log price change | 0.03228 | `P7_accuracy_by_horizon.csv` |
| h=30: error relative to tomorrow = today (geometric mean over items) | 1.001 | `P7_accuracy_by_horizon.csv` |
| h=30: mean absolute error in Tk | 79.17 | `P7_accuracy_by_horizon.csv` |
| h=30: direction accuracy on days the price moved | 0.38 | `P7_accuracy_by_horizon.csv` |
| h=30: bias in Tk (forecast - actual) | -6.393 | `P7_accuracy_by_horizon.csv` |
| h=1: Diebold-Mariano p-value vs tomorrow = today (supporting evidence) | 6.396e-05 | `P7_dm_vs_naive.csv` |
| h=7: Diebold-Mariano p-value vs tomorrow = today (supporting evidence) | 0.01103 | `P7_dm_vs_naive.csv` |
| h=14: Diebold-Mariano p-value vs tomorrow = today (supporting evidence) | 0.9169 | `P7_dm_vs_naive.csv` |
| h=30: Diebold-Mariano p-value vs tomorrow = today (supporting evidence) | 0.5 | `P7_dm_vs_naive.csv` |
| test origins | 87 | `P7_accuracy_by_horizon.csv` |
| scored forecasts | 17964 | `P7_accuracy_by_horizon.csv` |
| model beats tomorrow = today at every horizon (relative error < 1) | False | `P7_accuracy_by_horizon.csv` |

<!-- /S27 -->

<!-- S28 -->
## S28 ranges and alerts (shock episodes scored once)

Run 2026-11-16, code commit `8f74ac2`.

Command: `python -m fpw.runner S28`

File(s): `reports/project/tables/P8_event_scores.csv`

| measure | value | file |
|---|---|---|
| alert level (upper bound quantile) | 0.95 | `state/prereg_S28.yaml` |
| false alarms per item-year, 2024 non-event | 1.923 | `P8_level_curve.csv` |
| events detected | 11 | `P8_event_scores.csv` |
| events scored | 16 | `P8_event_scores.csv` |
| share of alert runs inside an event window | 0.06061 | `P8_alert_summary.csv` |
| alert runs | 429 | `P8_alert_summary.csv` |
| placebo p-value (random dates) | 0.2591 | `P8_alert_summary.csv` |
| placebo mean recall | 0.5925 | `P8_alert_summary.csv` |
| upper-bound coverage | 0.9413 | `P8_range_quality.csv` |
| Kupiec p-value | 3.578e-20 | `P8_range_quality.csv` |

<!-- /S28 -->

<!-- S29 -->
## S29 driver breakdown

Run 2026-11-16, code commit `8f74ac2`.

Command: `python -m fpw.runner S29`

File(s): `reports/project/tables/P9_driver_overall.csv`

| measure | value | file |
|---|---|---|
| share of the forecast change from calendar | 0.1383 | `P9_driver_overall.csv` |
| share of the forecast change from exchange_rate | 0.1699 | `P9_driver_overall.csv` |
| share of the forecast change from onion_export_measures | 0.09628 | `P9_driver_overall.csv` |
| share of the forecast change from price_history | 0.556 | `P9_driver_overall.csv` |
| share of the forecast change from weather | 0.03954 | `P9_driver_overall.csv` |
| largest spread of a group share across three refits | 0.5673 | `P9_driver_stability.csv` |
| alert days explained | 3081 | `outputs/export/alert_drivers.csv` |

<!-- /S29 -->

<!-- S30 -->
## S30 production export

Run 2026-11-16, code commit `b58aba5`.

Command: `python -m fpw.runner S30`

File(s): `outputs/export/forecasts.parquet`

| measure | value | file |
|---|---|---|
| items forecast | 54 | `outputs/export/forecasts.parquet` |
| forecast rows | 216 | `outputs/export/forecasts.parquet` |
| latest origin | 2026-10-24 | `outputs/export/forecasts.parquet` |
| range level | 0.95 | `outputs/export/forecasts.parquet` |
| rows without a range | 0 | `outputs/export/forecasts.parquet` |

<!-- /S30 -->
