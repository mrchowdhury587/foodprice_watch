# How to run the five notebooks (Colab, account mehedi11908015)

Open each notebook from GitHub with `?authuser=1`:
`https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/<name>.ipynb?authuser=1`

**Every notebook:** Runtime > Run all. The first time, click *Connect to Google Drive* and allow access (once per notebook, and again after a long idle).
Code is cloned from GitHub; data and results live in Drive `MyDrive/FoodPriceWatch`. A stage that is already finished is skipped, so a disconnect is safe: run all again.
After each notebook, copy the printed summary (last cell) to the assistant. A stage counts as done only from that output.

| Order | Notebook | Stages | Time | Then |
|---|---|---|---|---|
| 1 | `01_data_features` | S00, S22, S23 | ~10 min | already done once; re-run only if data changes |
| 2 | `02_model_selection_tuning` | S24, S25, S26 | 1-3 h (ETS, LSTM and 50 Optuna trials are slow) | **Paste the printed tuning JSON** and the "sha256" line. The assistant commits `state/prereg_S27.yaml` and pushes. |
| 3 | `03_test_evaluation` | S27 | ~30 min | needs the pushed pre-registration. Runs the 2025-26 test once. |
| 4 | `04_alerts_explanation` | S28, S29 | ~30 min | S28 first stops and prints `prereg_S28.yaml`: **paste it to the assistant**, who commits it; then run all again so it scores the 12 shock episodes. |
| 5 | `05_production_export` | S30 | ~5 min | writes `outputs/export/forecasts.parquet, alerts.csv, alert_drivers.csv` and the model (Drive only). |

| 6 | `06_view_and_download` | none | ~2 min | shows forecasts, alerts and driver sizes inside Colab and downloads two zip files (export files for the local dashboard; report tables, figures and results register) to your Downloads folder. |

If S25's winner is not LightGBM, S26-S29 stop and ask; tell the assistant.

## Dashboard (your computer)
```
.venv\Scripts\activate
pip install streamlit pandas pyarrow
streamlit run app/dashboard.py -- "G:\My Drive\FoodPriceWatch\outputs\export"
```
(use the path of the synced Drive folder, or download the three files into `outputs/export/`). The files hold TCB prices: do not commit or publish them.

## Updating with new prices
`python tools/update.py COMBINED.csv` checks the longer file and prints the steps (notebook 01 with S22 and S23, then notebook 05 with S30).
