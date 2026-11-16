# Run log

One entry per notebook run in Colab, taken from the pasted output of its last cell. A notebook counts as done only when it is logged here. Numbers here may be quoted in the report with the notebook and commit given.

## 01_data_intake (2026-11-17, account mhpcoder, code 647cf99)

The 4 raw files are in `MyDrive/FoodPriceWatch_v2/raw/`.

| file | bytes | sha256 | rows | first | last |
|---|---|---|---|---|---|
| tcb_dhaka_daily_prices_2021_2026.csv | 12,888,970 | ecda73328cc06ed2f6aed21858688e48cd72708d16df823ebabf71296043b76a | 76,440 | 2021-05-17 | 2026-10-24 |
| bd_ramadan_eid.csv | 7,237 | d42da0dd0bd93bfb85b1d5c31d48730e08531a6140e2a6bacca7d676910e0a03 | 24 | 2004-10-16 | 2027-02-09 |
| yahoo_bdt_per_usd.csv | 35,476 | c0a324b5d2630d4099877daa716e6e7063e9d4341e0dd70eeb8185bcce156fdd | 2,033 | 2019-01-01 | 2026-10-22 |
| weather_open_meteo_13_locations_2019_2026.csv | 3,100,649 | f58c38d2ea1f94843127fa07585adf8ae60bce9db0702586223494ad5d7807c9 | 37,037 | 2019-01-01 | 2026-10-19 |

The price file has 1,412 report days and 63 items. Each of the 8 focus items has 1,412 rows.

## 02_data_processing (2026-11-17, account mhpcoder, code 990215e)

| measure | value |
|---|---|
| panel rows (8 items x 1,412 report days) | 11,296 |
| not reported (blank price) | 8 |
| duplicate keys, Avg != mid, Min > Max, zero or negative | 0, 0, 0, 0 |
| report days in the 2022 gap | 24 |
| week-ago column matches the price 7 days earlier | 0.9961 |
| infinite values in features | 0 |
| items with weather / with exchange rate | 2 / 4 |
| driver values used before their availability date | 0 |
| driver values older than the 7-day cap | 0 |
| last report day with weather / exchange rate | 2026-10-24 / 2026-10-24 |
| comparison with the earlier run (panel, calendar, weather identical) | PASS |
| exchange rate before 2024-03-02: constant log offset / sd | 0.01499 / 0.0 (the earlier run scaled Yahoo by 1.0151) |
| exchange rate after 2024-03-02: mean abs diff of fx_lvl / fx_ch30 | 0.01457 / 0.00279 (the earlier run used the npm file) |

Per-item summary: `reports/tables/D1_panel_summary.csv`.

File hashes from this run were panel `04055f91f781a836…` and features `bd2667c5d317e625…`. After this run the CSV writer was fixed to LF line ends and 10 significant digits (code after 990215e), so checksums are the same on Windows and Colab. A rerun gives new checksums with the same content; the local run gives panel `e9ccc23e5bc71d88…`, features `99521b6bcb444d45…`.
