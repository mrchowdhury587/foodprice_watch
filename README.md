# Food Price Watch

**A Monitoring and Abnormal-Rise Alert System for Daily Retail Food Prices in Dhaka.** MSc project.

The system takes the Trading Corporation of Bangladesh (TCB) daily retail price sheets for Dhaka and works on 8 everyday items: chicken, local onion, eggs, potato, loose soybean oil, loose palm oil, imported garlic and sugar. For each item it builds an expected price range, flags prices that stay above that range, and compares three ways of setting the range.

Plan: [docs/PROJECT_PLAN_2026-11-17.md](docs/PROJECT_PLAN_2026-11-17.md). Settings: [config/settings.yaml](config/settings.yaml). Rules for working on the repo: [AGENTS.md](AGENTS.md).

## Notebooks (Colab)

| Notebook | Task | Status |
|---|---|---|
| [01_data_intake](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/01_data_intake.ipynb) | Copy the 4 raw files into `MyDrive/FoodPriceWatch_v2/raw/`, write `MANIFEST.csv` | ready |
| [02_data_processing](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/02_data_processing.ipynb) | One data table `processed/data_8.csv` (prices + calendar, weather, exchange rate), checks, comparison with the earlier run | ready |
| [03_price_behaviour](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/03_price_behaviour.ipynb) | How often and how much prices move, unchanged runs, price steps, sustained rise episodes (`processed/rise_episodes_8.csv`), before-Ramadan changes; tables B1-B6, figures F1-F2 | ready |
| 04_forecast_benchmark | "Tomorrow = today", ETS, LightGBM; choices on 2024 | planned |
| 05_alert_rules | ML range, simple range, fixed threshold, scored against sustained rises | planned |
| 06_report_tables | Final tables and figures | planned |

Code comes from GitHub `main` each session; Google Drive holds data and outputs only.

## Data

The code reads 4 raw files from `raw/`; none of them is in git:

| File | Content |
|---|---|
| `tcb_dhaka_daily_prices_2021_2026.csv` | TCB Dhaka daily retail prices, 2021-05-17 to 2026-10-24 |
| `bd_ramadan_eid.csv` | Ramadan and Eid dates |
| `yahoo_bdt_per_usd.csv` | Taka per US dollar, daily |
| `weather_open_meteo_13_locations_2019_2026.csv` | Daily weather at 13 locations (Open-Meteo) |

TCB publishes no reuse terms, so prices and anything derived from them stay out of this public repository.

Notebook 02 turns them into one table, `processed/data_8.csv`, with one row per item and report day (8 × 1,412 = 11,296 rows) and 20 columns:

| Columns | Meaning |
|---|---|
| Date, item_id | report day; item as "Product \| Unit" |
| Price_Min, Price_Max, Price_Avg | TCB's lowest and highest Dhaka price and their midpoint (Tk); blank = not reported |
| report_idx | report day number (0 = 2021-05-17), the time index for lags |
| gap_2022 | inside the sparse 2022 period (2022-03-12 to 2022-12-31): never filled across, never scored |
| days_since_prev_report | calendar days since the previous TCB sheet |
| reports_since_change | report days the price has stayed the same |
| month, dow, days_to_ramadan, days_to_eid_fitr, days_to_eid_adha, in_ramadan | calendar, known in advance |
| wx_tmax_7d, wx_tmean_30d, wx_rain_7d | Bangladesh 7-day max temperature, 30-day mean temperature, 7-day rain, usable 5 days late; Potato and Onion - Local only, blank for other items |
| fx_lvl, fx_ch30 | log taka per dollar and its 30-day change, as of the report day; Garlic - Imported, Soybean Oil, Palm Oil, Sugar only, blank for other items |

The item group (for reporting) and which items use weather or the exchange rate are set in `config/settings.yaml`. Lagged price changes, rolling averages and forecast targets depend on the horizon, so the forecasting notebook builds them from `Price_Avg`.

## Earlier work

The earlier pipeline (stages S00-S35, 54 items, report drafts) is kept unchanged in [archive/old_pipeline/](archive/old_pipeline/).
