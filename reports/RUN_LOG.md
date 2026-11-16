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

## 04a_forecast_choice (2026-11-17, LOCAL run on the work PC, code ae0b96c) — not a Colab run

Google Drive still would not mount in Colab, so with the user's approval the notebook ran locally on the same `data_8.csv` (sha256 `381ef71d10092bde…`). Only 2024 targets were scored. The choice below was written into `config/settings.yaml` (`forecast_choice`) and committed before notebook 04b was written or run. Tables: `reports/tables/M1_validation_grid.csv`, `M2_validation_models.csv`.

Result: on 2024 neither ETS nor LightGBM is below "tomorrow = today" at any horizon (relative MAE 1.00 to 1.11); the drivers make LightGBM worse; the simplest configuration wins.

```
validation origins: 43 | 2024-01-01 to 2024-11-24
=== 04a forecast choice on 2024 (validation year only) ===
code commit: ae0b96c (local run, work PC) | data_8.csv sha256 381ef71d10092bde
checks: PASS {'forecasts': 24768, 'scored': 24768, 'last_target_date': '2024-12-27', 'target_after_validation_year': 0, 'fit_after_origin': 0, 'rows_touching_gap': 0, 'naive_rel_mae': 1.0}
origins: 43 | horizons [1, 7, 14, 30] | rel = MAE of the model / MAE of "tomorrow = today" (below 1 = better than naive)

M1 LightGBM grid, geometric mean relative MAE over items (simplest first)
                                  config  rel_h1  rel_h7  rel_h14  rel_h30  rel_all  chosen
            price_only|leaves7|lr0.03|l1  1.1135  1.0294   1.0352   1.0137   1.0472    True
         price_only|leaves7|lr0.03|huber  2.0980  1.1342   1.0723   1.0009   1.2641   False
            price_only|leaves7|lr0.05|l1  1.2186  1.0334   1.0620   1.0404   1.0861   False
         price_only|leaves7|lr0.05|huber  2.1506  1.1506   1.0801   1.0366   1.2902   False
           price_only|leaves31|lr0.03|l1  1.3157  1.0932   1.0935   1.0554   1.1351   False
        price_only|leaves31|lr0.03|huber  2.2093  1.2096   1.1475   1.1247   1.3628   False
           price_only|leaves31|lr0.05|l1  1.4376  1.1388   1.1177   1.0763   1.1847   False
        price_only|leaves31|lr0.05|huber  2.3354  1.2329   1.1768   1.1576   1.4073   False
    price_plus_drivers|leaves7|lr0.03|l1  1.3575  1.0828   1.0594   1.0050   1.1185   False
 price_plus_drivers|leaves7|lr0.03|huber  2.5955  1.1863   1.0960   1.0147   1.3603   False
    price_plus_drivers|leaves7|lr0.05|l1  1.4557  1.0885   1.0654   1.0217   1.1460   False
 price_plus_drivers|leaves7|lr0.05|huber  2.5939  1.2155   1.1369   1.0467   1.3918   False
   price_plus_drivers|leaves31|lr0.03|l1  1.6171  1.1651   1.1450   1.0803   1.2356   False
price_plus_drivers|leaves31|lr0.03|huber  2.6731  1.2821   1.1781   1.0941   1.4498   False
   price_plus_drivers|leaves31|lr0.05|l1  1.8044  1.2124   1.1887   1.1238   1.3075   False
price_plus_drivers|leaves31|lr0.05|huber  2.9850  1.3246   1.2348   1.1396   1.5358   False

M2 naive, ETS and the chosen LightGBM by horizon (2024); dm_stat > 0 = worse than naive, < 0 = better; p_holm = Holm-corrected p; NaN = not computable
model  horizon     n  mae_log  mae_log_naive  gmean_rel_mae  mae_tk  mae_tk_naive  accuracy  accuracy_naive  direction_acc  dm_stat  p_holm
  ets        1 344.0  0.00891        0.00858        1.05958 0.95480       0.92442   0.99103         0.99135        0.44776  3.76370 0.00308
  ets        7 344.0  0.03184        0.03158        1.01046 3.53377       3.50872   0.96784         0.96808        0.36538  2.92939 0.02735
  ets       14 344.0  0.05085        0.05069        1.00407 5.40724       5.39244   0.94835         0.94851        0.35385  2.16121 0.14571
  ets       30 344.0  0.08274        0.08261        1.00228 8.53395       8.52471   0.91401         0.91410        0.33221  1.71487 0.28122
 lgbm        1 344.0  0.00929        0.00858        1.11355 1.00857       0.92442   0.99065         0.99135        0.71642  3.95709 0.00201
 lgbm        7 344.0  0.03222        0.03158        1.02937 3.64664       3.50872   0.96746         0.96808        0.53846  1.28633 0.41075
 lgbm       14 344.0  0.05193        0.05069        1.03522 5.57885       5.39244   0.94705         0.94851        0.52308  0.78991 0.43402
 lgbm       30 344.0  0.08231        0.08261        1.01365 8.46509       8.52471   0.91337         0.91410        0.54362      NaN     NaN
naive        1 344.0  0.00858        0.00858        1.00000 0.92442       0.92442   0.99135         0.99135        0.00000      NaN     NaN
naive        7 344.0  0.03158        0.03158        1.00000 3.50872       3.50872   0.96808         0.96808        0.00000      NaN     NaN
naive       14 344.0  0.05069        0.05069        1.00000 5.39244       5.39244   0.94851         0.94851        0.00000      NaN     NaN
naive       30 344.0  0.08261        0.08261        1.00000 8.52471       8.52471   0.91410         0.91410        0.00000      NaN     NaN
ets: below naive at horizons none
lgbm: below naive at horizons none

CHOICE (to be committed before 04b):
forecast_choice:
  config: price_only|leaves7|lr0.03|l1
  feature_set: price_only
  params: {'num_leaves': 7, 'learning_rate': 0.03, 'objective': 'l1'}
  validation_rel_mae: 1.0472
  chosen_by: notebook 04a, code ae0b96c (local run, work PC), 2024 origins only
```

## 04b_forecast_test (2026-11-17, LOCAL run on the work PC, code c4b683f) — RETROSPECTIVE, not a Colab run

Google Drive still would not mount in Colab, so the notebook ran locally on the same `data_8.csv` (sha256 `381ef71d10092bde…`), with the user's approval. The LightGBM configuration was fixed on 2024 and committed in 8d7c145 before this notebook was written or run. 2025-26 was already scored by the earlier run, so these results are retrospective. Tables: `reports/tables/M3_test_accuracy.csv`, `M4_test_by_item.csv`. Forecast files (contain prices) are on the work PC only until a Colab rerun: `processed/forecasts_test.csv`, `processed/forecasts_h7.csv`.

Result: neither ETS nor LightGBM is below "tomorrow = today" at any horizon (relative MAE 1.01 to 1.21); where the difference is significant (DM, Holm p < 0.05) it favours naive.

```
chosen on 2024: price_only|leaves7|lr0.03|l1 | choice first committed in 8d7c145 2026-11-17
test origins: 82 | 2025-01-01 to 2026-09-16
=== 04b forecast test, 2025-01-01 to 2026-10-24: RETROSPECTIVE ===
code commit: c4b683f (local run, work PC) | data_8.csv sha256 381ef71d10092bde
model choice (2024 only): price_only|leaves7|lr0.03|l1 | choice first committed in 8d7c145 2026-11-17
checks: PASS {'test_forecasts': 7872, 'test_scored': 7872, 'first_target_date': '2025-01-02', 'last_target_date': '2026-10-16', 'target_before_test': 0, 'fit_after_origin': 0, 'rows_touching_gap': 0, 'naive_rel_mae': 1.0, 'h7_rows_per_model': 8488, 'h7_rows_expected': 8488, 'h7_first_origin': '2023-06-02', 'h7_last_origin': '2026-10-24'}

M3 accuracy by model and horizon; rel = MAE / MAE of "tomorrow = today"; dm_stat > 0 = worse than naive; NaN = not computable
model  horizon     n  mae_log  mae_log_naive  gmean_rel_mae  mae_tk  mae_tk_naive  accuracy  accuracy_naive  direction_acc  dm_stat  p_holm
  ets        1 656.0  0.00603        0.00541        1.12695 0.52839       0.49924   0.99401         0.99463        0.39175  5.72277 0.00000
  ets        7 656.0  0.02610        0.02536        1.02813 2.48265       2.44588   0.97382         0.97454        0.40176  2.60809 0.04158
  ets       14 656.0  0.04168        0.04067        1.01854 3.79460       3.75991   0.95814         0.95906        0.42308  2.09069 0.07938
  ets       30 656.0  0.06505        0.06342        1.02010 5.84904       5.78887   0.93313         0.93446        0.39216  3.90938 0.00096
 lgbm        1 656.0  0.00626        0.00541        1.21301 0.56801       0.49924   0.99377         0.99463        0.46392  7.59564 0.00000
 lgbm        7 656.0  0.02640        0.02536        1.03344 2.49918       2.44588   0.97348         0.97454        0.54545  4.85789 0.00003
 lgbm       14 656.0  0.04161        0.04067        1.01427 3.77381       3.75991   0.95804         0.95906        0.50452  2.62358 0.04158
 lgbm       30 656.0  0.06515        0.06342        1.02208 5.79800       5.78887   0.93200         0.93446        0.56863  1.09859 0.27520
naive        1 656.0  0.00541        0.00541        1.00000 0.49924       0.49924   0.99463         0.99463        0.00000      NaN     NaN
naive        7 656.0  0.02536        0.02536        1.00000 2.44588       2.44588   0.97454         0.97454        0.00000      NaN     NaN
naive       14 656.0  0.04067        0.04067        1.00000 3.75991       3.75991   0.95906         0.95906        0.00000      NaN     NaN
naive       30 656.0  0.06342        0.06342        1.00000 5.78887       5.78887   0.93446         0.93446        0.00000      NaN     NaN
ets: below naive at horizons none; significantly better (DM, Holm p < 0.05) at none
lgbm: below naive at horizons none; significantly better (DM, Holm p < 0.05) at none

M4 relative MAE by item at horizon 7 (below 1 = better than naive)
model                  ets   lgbm  naive
item_id                                 
Chicken - Broiler    1.000  1.003    1.0
Egg - Farm           1.001  1.030    1.0
Garlic - Imported    1.004  1.015    1.0
Onion - Local        1.006  1.020    1.0
Palm Oil - Loose     1.007  1.045    1.0
Potato               1.096  1.116    1.0
Soybean Oil - Loose  1.094  0.996    1.0
Sugar                1.023  1.047    1.0

files: processed/forecasts_test.csv sha256 d536b5039e841ea6 | processed/forecasts_h7.csv sha256 6449ec4dbf7b5a5c | rows 16976
```

## 05a_alert_choice (2026-11-17, LOCAL run on the work PC, code 2549097) — not a Colab run

Run locally against `E:\msc_project\FoodPriceWatch_v2_local` (Drive does not mount in Colab). Only 2024 was used. The settings below were written into `config/settings.yaml` (`alert_choice`) and committed before notebook 05b was written or run. Table: `reports/tables/A1_alert_choice.csv`.

```
=== 05a alert settings chosen on 2024 (validation year only) ===
code commit: 2549097 (local run, work PC) | forecasts_h7.csv sha256 6449ec4dbf7b5a5c
checks: PASS {'rows_lgbm': 8488, 'rows_naive': 8488, 'one_row_per_report_day': True, 'naive_error_is_change': True, 'episodes_same_as_03': True, 'episodes_2024': 11, 'first_target_date': '2023-06-13', 'first_bound_date': '2023-09-07'}
2024: episodes 11 | item-years 10.53 | target: runs matching no rise <= 2.0 per item-year

A1 every candidate on 2024 (setting = range level for A and B, threshold for C)
rule  setting  episodes  detected  recall  alert_runs  matched_runs  precision  unmatched_per_item_year  median_delay_reports  chosen
   A    0.900        11         9  0.8182          39             9     0.2308                   2.8495                   0.0   False
   A    0.950        11         6  0.5455          17             6     0.3529                   1.0448                   1.5    True
   A    0.975        11         5  0.4545          13             5     0.3846                   0.7599                   2.0   False
   A    0.990        11         4  0.3636          10             4     0.4000                   0.5699                   2.0   False
   B    0.900        11         9  0.8182          36             9     0.2500                   2.5646                   2.0   False
   B    0.950        11         8  0.7273          20             8     0.4000                   1.1398                   2.0    True
   B    0.975        11         5  0.4545          14             5     0.3571                   0.8549                   2.0   False
   B    0.990        11         4  0.3636          11             4     0.3636                   0.6649                   2.0   False
   C    0.030        11        10  0.9091          58            10     0.1724                   4.5593                  -4.0   False
   C    0.050        11        10  0.9091          39            10     0.2564                   2.7546                  -1.5   False
   C    0.070        11        10  0.9091          27            10     0.3704                   1.6147                   0.5    True
   C    0.100        11         9  0.8182          15             9     0.6000                   0.5699                   2.0   False

CHOICE (to be committed before 05b):
alert_choice:
  A: {setting: 0.95, target_met: true}   # ML range (LightGBM)
  B: {setting: 0.95, target_met: true}   # simple range ("tomorrow = today")
  C: {setting: 0.07, target_met: true}   # fixed 7-report rise
  chosen_by: notebook 05a, code 2549097 (local run, work PC), 2024 only
```

## 05b_alert_scoring (2026-11-17, LOCAL run on the work PC, code aa8c8aa) — 2025-26 RETROSPECTIVE, not a Colab run

Run locally against `E:\msc_project\FoodPriceWatch_v2_local` (Drive does not mount in Colab). Settings fixed on 2024 and committed in e0cfa06 before this notebook was written or run. Tables: `reports/tables/A2_rule_comparison.csv`, `A3_rule_overlap.csv`, `A4_range_coverage.csv`, `A5_alerts_by_item.csv`. Alert flags (`processed/alerts_8.csv`) are in the local data folder only.

Result: every rule catches far more sustained rises than random dates (p = 0.003, the smallest possible with 300 draws). The ML range and the simple range catch nearly the same rises (2024: 6 vs 8; 2025-26: 17 vs 15; their errors correlate at 0.99), so the alerts do not depend on the ML model. The fixed 7 % rule catches the most (10/11, 22/23), but it is close to the rise definition it is scored against. Range coverage is 0.93-0.95 against 0.95 nominal; in 2025-26 it is significantly below nominal (Kupiec p < 0.001).

```
settings (chosen on 2024): {'A': 0.95, 'B': 0.95, 'C': 0.07} | first committed in e0cfa06 2026-11-17
=== 05b alert rules vs sustained 10 % rises: 2024 validation and 2025-26 RETROSPECTIVE ===
code commit: aa8c8aa (local run, work PC) | forecasts_h7.csv sha256 6449ec4dbf7b5a5c
settings fixed on 2024: {'A': 0.95, 'B': 0.95, 'C': 0.07} | first committed in e0cfa06 2026-11-17
checks: PASS {'placebo_p_valid': True, 'same_as_05a': True, 'first_alert_date': '2023-06-25', 'episodes_per_period': {'2024 validation': 11, '2025-26 retrospective': 23}, 'corr_errors_A_B': 0.9907}

A2 rule comparison (recall = rises caught; precision = alert runs that match a rise; delay in report days after onset)
               period rule  setting  episodes  detected  recall  placebo_recall  placebo_p  alert_runs  precision     f1  median_delay_reports  runs_per_item_year  unmatched_per_item_year
      2024 validation    A     0.95        11         6  0.5455          0.1970     0.0033          17     0.3529 0.4286                   1.5              1.6147                   1.0448
      2024 validation    B     0.95        11         8  0.7273          0.2961     0.0033          20     0.4000 0.5161                   2.0              1.8997                   1.1398
      2024 validation    C     0.07        11        10  0.9091          0.4909     0.0033          27     0.3704 0.5263                   0.5              2.5646                   1.6147
2025-26 retrospective    A     0.95        23        17  0.7391          0.2849     0.0033          42     0.4048 0.5231                   2.0              2.1766                   1.2956
2025-26 retrospective    B     0.95        23        15  0.6522          0.2506     0.0033          39     0.3846 0.4839                   2.0              2.0211                   1.2438
2025-26 retrospective    C     0.07        23        22  0.9565          0.3123     0.0033          30     0.7333 0.8302                   2.0              1.5547                   0.4146

A3 rises caught by the ML range (A) and the simple range (B)
               period  episodes  both  A_only  B_only  neither
      2024 validation        11     6       0       2        3
2025-26 retrospective        23    15       2       0        6

A4 range coverage (share of days at or below the upper bound; nominal = level)
               period rule    n  nominal  coverage  kupiec_p
      2024 validation    A 2632     0.95    0.9445    0.2053
      2024 validation    B 2632     0.95    0.9460    0.3582
2025-26 retrospective    A 4824     0.95    0.9345    0.0000
2025-26 retrospective    B 4824     0.95    0.9391    0.0007

A5 per item: rises caught / episodes (alert runs)
period              2024 validation                    2025-26 retrospective                  
rule                              A        B         C                     A        B        C
item_id                                                                                       
Chicken - Broiler           1/1 (3)  1/1 (4)   1/1 (5)               1/3 (4)  1/3 (4)  2/3 (3)
Egg - Farm                  1/1 (1)  1/1 (1)   1/1 (3)               3/3 (7)  3/3 (6)  3/3 (4)
Garlic - Imported           1/2 (1)  1/2 (1)   1/2 (1)               4/4 (7)  4/4 (8)  4/4 (7)
Onion - Local               2/4 (2)  3/4 (3)  4/4 (10)               5/7 (6)  5/7 (6)  7/7 (9)
Palm Oil - Loose            0/0 (3)  0/0 (3)   0/0 (0)               0/0 (4)  0/0 (4)  0/0 (0)
Potato                      1/3 (2)  2/3 (3)   3/3 (8)               4/6 (5)  2/6 (3)  6/6 (6)
Soybean Oil - Loose         0/0 (3)  0/0 (3)   0/0 (0)               0/0 (4)  0/0 (3)  0/0 (0)
Sugar                       0/0 (2)  0/0 (2)   0/0 (0)               0/0 (5)  0/0 (5)  0/0 (1)

2024 validation | A ML range: caught 6/11 = 0.55 vs random dates 0.20 (p = 0.003); 17 alert runs
2024 validation | B simple range: caught 8/11 = 0.73 vs random dates 0.30 (p = 0.003); 20 alert runs
2024 validation | C fixed 7-report rise: caught 10/11 = 0.91 vs random dates 0.49 (p = 0.003); 27 alert runs
2024 validation: the simple range catches more rises than the ML range (8 vs 6)
2025-26 retrospective | A ML range: caught 17/23 = 0.74 vs random dates 0.28 (p = 0.003); 42 alert runs
2025-26 retrospective | B simple range: caught 15/23 = 0.65 vs random dates 0.25 (p = 0.003); 39 alert runs
2025-26 retrospective | C fixed 7-report rise: caught 22/23 = 0.96 vs random dates 0.31 (p = 0.003); 30 alert runs
2025-26 retrospective: the simple range catches fewer rises than the ML range (15 vs 17)

alerts file: processed/alerts_8.csv | rows 25464 | sha256 613b3c4595a68cf5
```
