# Data collection: getting new TCB price reports into the project

Three steps, all on the work PC, all standard-library Python. The agent never downloads from TCB; the user runs step 1.

```
tcb.gov.bd  --1 download-->  Downloads/TCB_Daily_RMP/*.xlsx  --2 convert-->  CONVERTED.csv  --3 append-->  tcb_dhaka_daily_prices_2021_2026_v2.csv
```

## 1. Download (user)

```
python tools/tcb_download.py
```

Fetches the daily retail price reports (Bangla Excel) into `Downloads/TCB_Daily_RMP`. Files already there are skipped, so re-running only adds new report days.

## 2. Convert

```
python tools/tcb_convert.py --in "%USERPROFILE%\Downloads\TCB_Daily_RMP" --out-csv CONVERTED.csv
```

Reads every `.xlsx` in the folder and writes one English CSV (one row per date and item) plus a formatted Excel copy with a `Files_Log` and an `Untranslated` sheet. It refuses to overwrite an existing output file. Run with no options it behaves as the original script did (writes `TCB_Combined_English.*` to Downloads).

Read the summary it prints:

| Line | Expected | If not |
|---|---|---|
| Files FAILED | 2 (`4e7e7502...`, `c3d4e7ac...`: not real Excel files) | a new failure is a report day that is missing: re-download that file |
| Duplicates | 3 (a second file for a date already read) | more is harmless; the first file per date is used |
| Distinct items | 63 | a new item needs `--allow-new-series` in step 3 and a DEVIATIONS.md entry |
| Untranslated | 0 names, 0 auto-translated | add the Bangla name to `tools/my_translations.csv` (`bangla name,English name,Category`) and convert again |

## 3. Append

```
python tools/tcb_append.py --base tcb_dhaka_daily_prices_2021_2026.csv --new CONVERTED.csv --out tcb_dhaka_daily_prices_2021_2026_v2.csv --after-last-base-date
```

- Drops the converter's 5 extra columns (Year, Month, Weekday, Translation, Source_File) and writes numbers the way the base file does.
- `--after-last-base-date` uses only report days later than the base file's last day. The base file holds hand corrections (`corrections.csv`) that a fresh conversion does not; without the option those rows are reported as conflicts and nothing is written.
- Stops and writes nothing if a new row has a non-ISO date, a duplicate key, a zero or negative price, Min > Max, Avg different from (Min+Max)/2, or an unknown series.
- Never changes the base file and never overwrites an existing output file.

## 4. Hand over

Put the new CSV in `MyDrive/FoodPriceWatch/inbox/project/` under the name set in `config/project.yaml` (`price_file`). S00 intake copies it into `data/raw/project/` and records its SHA-256; stage S22 builds the panel from it and checks that every date up to 2026-10-24 is unchanged. `data/raw/` is never edited by hand.

## 5. Audit (work PC, needs openpyxl in `.venv`)

```
.venv\Scripts\python tools\tcb_audit.py --prices tcb_dhaka_daily_prices_2021_2026_v2.csv --sample audit_sample_2pct.csv --candidates audit_candidates.csv --corrections corrections.csv --originals "%USERPROFILE%\Downloads\TCB_Daily_RMP" --out-dir reports\project\tables
```

For each of the 1,530 sampled (date, item) rows it opens the original Excel file, finds the row by its Bangla name and unit, and compares today's minimum and maximum with the CSV. It reads the Excel file with openpyxl and does not use the converter, so a converter mistake would show. It measures transcription (file to CSV) only: a number TCB itself typed wrongly cannot be detected this way and stays flagged. Two things it handles: a workbook with spare sheets (the sheet carrying the report date is used) and the list of changed items at the bottom of a sheet (not part of the price table).

Result 2026-11-15: 1,530 of 1,530 rows checked, 0 mismatches (95% upper bound 0.25% of rows); the 5 ginger candidates equal the original files, so they are kept and stay flagged. Three wrong prices planted in a copy were all found.

## Checks behind these tools (run 2026-11-15 on the work PC)

1. Re-translating `Product_Bangla` and `Unit_Bangla` of all 76,440 rows of the base file with `tcb_convert.py` reproduces `Product` and `Unit` with 0 mismatches.
2. The base file cut at 2026-09-30, plus the converter's output for all days up to 2026-10-24, appended with `--after-last-base-date`, gives a file byte-identical to the base file (same SHA-256).
3. Converting the folder twice gives identical output.
4. `tests/test_tools_append.py` covers the column drop, the date cut, the conflict stop and the no-overwrite rule on a small made-up file.

Note: `tools/tcb_convert.py` is the user's converter from `BD_Food_Price_Watch.zip` (`scripts/tcb_convert.py`, 2026-10-25) with a command-line wrapper added at the end. It was rebuilt into the repo on 2026-11-15 because the earlier commit d8f67f0 was never pushed and its patch file could not be found.
