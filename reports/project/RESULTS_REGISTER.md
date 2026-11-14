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
