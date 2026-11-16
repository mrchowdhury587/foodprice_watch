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

## 02_data_processing (2026-11-17, account mhpcoder, code 2a93d78) — current

One data table `processed/data_8.csv`: 11,296 rows, 20 columns, sha256 `381ef71d10092bde…` (identical to the local run), checks PASS.

| measure | value |
|---|---|
| items / report days | 8 / 1,412 (2021-05-17 to 2026-10-24) |
| not reported (blank price) | 8 |
| duplicate keys, Avg != mid, Min > Max, zero or negative | 0, 0, 0, 0 |
| report days in the 2022 gap | 24 |
| week-ago column matches the price 7 days earlier | 0.9961 |
| infinite values | 0 |
| items with weather / with exchange rate | 2 / 4 |
| driver values used before their availability date | 0 |
| driver values older than the 7-day cap | 0 |
| driver empty on an item that uses it / driver on an item that does not | 0 / 0 |
| last report day with weather / exchange rate | 2026-10-24 / 2026-10-24 |
| comparison with the earlier run (prices, day numbers, calendar, weather identical) | PASS |
| exchange rate before 2024-03-02: constant log offset / sd | 0.01499 / 0.0 (the earlier run scaled Yahoo by 1.0151) |
| fx_ch30 before 2024-03-02: mismatches where the earlier run had a value / values now filled where it was empty | 0 / 624 |
| exchange rate after 2024-03-02: mean abs diff of fx_lvl / fx_ch30 | 0.01457 / 0.00292 (the earlier run used the npm file) |

Per-item summary: `reports/tables/D1_panel_summary.csv` (unchanged).

## 02_data_processing (2026-11-17, account mhpcoder, code 990215e) — superseded by the run above

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

File hashes from this run were panel `04055f91f781a836…` and features `bd2667c5d317e625…`.

**This run is superseded; notebook 02 must be rerun.** After it, three things changed:
- The CSV writer now uses LF line ends and 10 significant digits, so checksums match on Windows and Colab.
- `fx_ch30` was fixed: it was empty on 28 % of report days for the exchange-rate items (see `DEVIATIONS.md`).
- The two files are merged into one, `processed/data_8.csv` (20 columns).

The local run of the current code gives `data_8.csv` sha256 `381ef71d10092bde…`, with every check passing and the comparison with the earlier run passing.

## 03_price_behaviour (2026-11-17, LOCAL run on the work PC, code e8853d5) — not a Colab run

Colab could not mount Google Drive this session ("credential propagation was unsuccessful", repeated for the GitHub notebook, a copy saved in Drive and a private window). With the user's approval the notebook was run locally on the work PC (see `DEVIATIONS.md`). The input is the same file: local `data_8.csv` sha256 `381ef71d10092bde…`, identical to the Colab run of notebook 02. To be rerun in Colab once Drive mounts again; that run replaces this entry if its output differs.

Outputs on the work PC only (not yet on Drive): `processed/rise_episodes_8.csv` (sha256 `48d529fceedeae9b…`), `reports/figures/F2_prices_with_rises.png` (contains prices). Committed: `reports/tables/B1`-`B6`, `reports/figures/F1_change_frequency.png` (rates only).

```
=== 03 price behaviour summary ===
code commit: e8853d5 (local run, work PC) | data_8.csv sha256 381ef71d10092bde
checks: PASS {'changes_counted': 11074, 'change_inside_or_across_gap': 0, 'rise_window_touching_gap': 0, 'episodes_10pct': 70, 'episode_onsets_in_gap': 0}
rise rule: R over 14 report days >= 0.1 for >= 5 report days; merge gap 14

B1 share of report days with a change, by year (2021 from 17 May; 2022 = 1 Jan to 11 Mar, before the gap; 2026 to 24 Oct)
            item_id   2021   2022   2023   2024   2025   2026    all
  Chicken - Broiler 0.5290 0.4750 0.4517 0.3921 0.3413 0.2193 0.3752
         Egg - Farm 0.4052 0.3000 0.3089 0.2553 0.1737 0.0781 0.2290
  Garlic - Imported 0.4706 0.2000 0.3127 0.2067 0.1467 0.1784 0.2355
      Onion - Local 0.4510 0.4500 0.3900 0.3526 0.2425 0.2045 0.3179
   Palm Oil - Loose 0.4323 0.4250 0.1737 0.1277 0.2036 0.0818 0.1883
             Potato 0.2941 0.2750 0.3243 0.2401 0.1886 0.0743 0.2182
Soybean Oil - Loose 0.4575 0.3611 0.1158 0.1398 0.2305 0.1190 0.1942
              Sugar 0.2968 0.0750 0.1583 0.1216 0.0868 0.0558 0.1255

B2 size of a change (on days it changed)
            item_id  changes  share_up  median_abs_tk  p95_abs_tk  median_abs_pct  p95_abs_pct  largest_up_pct  largest_down_pct
  Chicken - Broiler      520    0.5192            5.0        12.5            2.70         7.58           16.22            -14.29
         Egg - Farm      317    0.5237            1.0         3.5            2.35         6.90           12.20            -10.53
  Garlic - Imported      326    0.4939            5.0        20.0            4.00        12.91           20.00            -19.35
      Onion - Local      440    0.4977            2.5        12.5            5.00        16.72           42.31            -25.00
   Palm Oil - Loose      261    0.5709            1.5         5.0            1.02         3.74            8.36             -5.56
             Potato      302    0.4901            2.5         5.0            6.25        18.18           36.36            -23.08
Soybean Oil - Loose      268    0.5896            1.5         5.0            0.88         3.01            4.23             -8.38
              Sugar      174    0.5000            2.0         5.0            1.85         4.76            7.41             -7.32

B3 unchanged runs (report days)
            item_id  runs  mean_days  median_days  p90_days  longest_days longest_from longest_to
  Chicken - Broiler   304       2.85          2.0       6.0            40   2026-08-14 2026-09-24
         Egg - Farm   198       5.39          3.0      12.0            44   2025-12-02 2026-01-18
  Garlic - Imported   219       4.83          3.0      11.2            40   2025-12-15 2026-01-27
      Onion - Local   267       3.54          2.0       8.0            32   2025-08-07 2025-09-09
   Palm Oil - Loose   171       6.58          3.0      13.0           102   2026-05-18 2026-09-07
             Potato   201       5.38          3.0      12.0            75   2026-08-06 2026-10-24
Soybean Oil - Loose   183       6.08          3.0      13.8            50   2025-10-30 2025-12-19
              Sugar   133       9.11          4.0      23.8           104   2026-04-27 2026-08-18

B4 price step (Tk)
            item_id  smallest_step_tk  most_common_step_tk  share_steps_multiple_of_0_5
  Chicken - Broiler               1.0                  5.0                          1.0
         Egg - Farm               0.5                  1.0                          1.0
  Garlic - Imported               2.5                  5.0                          1.0
      Onion - Local               1.0                  2.5                          1.0
   Palm Oil - Loose               0.5                  1.0                          1.0
             Potato               0.5                  2.5                          1.0
Soybean Oil - Loose               0.5                  1.0                          1.0
              Sugar               0.5                  2.5                          1.0

B5 sustained rise episodes by onset year (10 % rule)
            item_id  2021  2022  2023  2024  2025  2026
  Chicken - Broiler     2     0     2     1     1     2
         Egg - Farm     2     1     1     1     1     2
  Garlic - Imported     2     0     4     2     1     3
      Onion - Local     2     1     5     4     4     3
   Palm Oil - Loose     0     1     0     0     0     0
             Potato     3     1     5     3     3     3
Soybean Oil - Loose     0     1     0     0     0     0
              Sugar     1     0     2     0     0     0
validation 2024: episodes 7 % / 10 % / 15 % = 17 / 11 / 8 | items with no 10 % episode: ['Palm Oil - Loose', 'Soybean Oil - Loose', 'Sugar']
retrospective 2025-26: episodes 7 % / 10 % / 15 % = 26 / 23 / 15 | items with no 10 % episode: ['Palm Oil - Loose', 'Soybean Oil - Loose', 'Sugar']

B6 before Ramadan vs other days (descriptive; 14-report change; before Ramadan = 1 to 30 days before its first day)
            item_id  days_before_ramadan  ramadans  median_change_before_ramadan_pct  median_change_other_days_pct  share_rise_days_before_ramadan  share_rise_days_other
  Chicken - Broiler                  112         5                              2.94                           0.0                          0.1607                 0.1114
         Egg - Farm                  112         5                             -2.47                           0.0                          0.0000                 0.0730
  Garlic - Imported                  112         5                              0.00                           0.0                          0.0268                 0.1267
      Onion - Local                  112         5                             -4.55                           0.0                          0.1786                 0.2518
   Palm Oil - Loose                  112         5                              0.00                           0.0                          0.0357                 0.0040
             Potato                  112         5                             -9.76                           0.0                          0.0893                 0.2446
Soybean Oil - Loose                  110         5                              0.00                           0.0                          0.0091                 0.0064
              Sugar                  112         5                              0.00                           0.0                          0.0000                 0.0240

rise episodes file: processed/rise_episodes_8.csv | rows 70 | sha256 48d529fceedeae9b
figures: ['F1_change_frequency.png', 'F2_prices_with_rises.png']
```
