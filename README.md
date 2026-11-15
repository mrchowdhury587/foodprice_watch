# Bangladesh Food Price Watch

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/run_stage.ipynb)

Master's project (not a thesis): a price-prediction system for TCB daily retail prices in Dhaka (63 items, May 2021 onward).
For each item it forecasts the price 1, 7, 14 and 30 report days ahead with an expected range, raises an alert when the
price stays above the range, and attaches a driver breakdown to each alert. One LightGBM model serves all items and horizons.
Scope and "done": `SPEC.md`. Plan: `docs/PROJECT_PLAN_2026-11-15.md`. Stage status: `state/stages.json`, `PROGRESS.md`.

## Run it in Colab

- **GitHub holds code only.** Every session the notebook clones `main` into `/content/foodprice_watch`.
- **Google Drive holds data and outputs only**, in `MyDrive/FoodPriceWatch/` (`inbox/`, `data/`, `outputs/`, `models/`, `state/`). Data is not in this public repo (TCB reuse terms are unconfirmed).

1. Put the project data files in `MyDrive/FoodPriceWatch/inbox/project/`.
2. Click **Open in Colab**, run the cells top to bottom, set `STAGE`, run the stage cell, paste the summary back.

After a disconnect, reconnect and run the same cells again; long jobs skip units already saved on Drive.

## Layout

- `src/fpw/` library: paths, loaders, panel, features, checkpoints, stage registry and runner
- `src/stages/` one script per stage (S00 intake, S22 panel, S23 features); `finalize.py` runs a stage's tests and marks it done
- `tests/` acceptance tests; `config/project.yaml` settings of the prediction system
- `tools/` data collection helpers run on the work PC (convert, download, append, audit)
- `state/` ledger, pre-registrations, seals; `reports/` tables, figures, results register
- `archive/` frozen earlier comparison study (S00-S11) and retired instructions; not run
- `AGENTS.md`, `SPEC.md`, `DECISIONS.md`, `DEVIATIONS.md`, `PROGRESS.md`, `docs/`: rules, scope, choices, log

Author: to be confirmed (`config.yaml` author).
