# Food Price Watch

**A Monitoring and Abnormal-Rise Alert System for Daily Retail Food Prices in Dhaka.** MSc project.

The system takes the Trading Corporation of Bangladesh (TCB) daily retail price sheets for Dhaka and works on 8 everyday items: chicken, local onion, eggs, potato, loose soybean oil, loose palm oil, imported garlic and sugar. For each item it builds an expected price range, flags prices that stay above that range, and compares three ways of setting the range.

Plan: [docs/PROJECT_PLAN_2026-11-17.md](docs/PROJECT_PLAN_2026-11-17.md). Settings: [config/settings.yaml](config/settings.yaml). Rules for working on the repo: [AGENTS.md](AGENTS.md).

## Notebooks (Colab)

| Notebook | Task | Status |
|---|---|---|
| [01_data_intake](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/01_data_intake.ipynb) | Copy the 4 raw files into `MyDrive/FoodPriceWatch_v2/raw/`, write `MANIFEST.csv` | ready |
| [02_data_processing](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/02_data_processing.ipynb) | 8-item panel and driver features, checks, comparison with the earlier run | ready |
| 03_price_behaviour | How often and how much prices move; rise episodes | planned |
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

## Earlier work

The earlier pipeline (stages S00-S35, 54 items, report drafts) is kept unchanged in [archive/old_pipeline/](archive/old_pipeline/).
