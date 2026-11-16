# AGENTS.md: Food Price Watch

## What this is
A master's project: **Food Price Watch: A Monitoring and Abnormal-Rise Alert System for Daily Retail Food Prices in Dhaka.**
It uses TCB's daily Dhaka retail prices for 8 everyday items. It gives each item an expected price range, raises an alert when the price stays above it, and compares ways of building those alerts (a machine-learning range, a simple "tomorrow = today" range, a fixed threshold). The forecast models are reported as a benchmark, not as the product.

- Plan: `docs/PROJECT_PLAN_2026-11-17.md`.
- Settings: `config/settings.yaml`.
- Changes to the plan: `DEVIATIONS.md`.
- Earlier pipeline (stages S00-S35), its results and its report: `archive/old_pipeline/`. Read-only; never edit or rerun it.

## Layout
- `src/foodwatch/`: the code (paths, load, panel, features, checks). The notebooks call it.
- `notebooks/NN_<task>.ipynb`: one notebook per task, run in Colab. Each starts with the same three setup cells (mount Drive, clone `main`, set paths) and ends with a printed summary.
- `tools/`: TCB download, convert, append and audit scripts (work PC).
- Data and outputs live on Drive in `MyDrive/FoodPriceWatch_v2` (`raw/`, `processed/`, `reports/tables/`), never in git.

## Working rules
- One notebook, one task. Write the code, run a local dry run where the data allows it, then the user runs the notebook in Colab and pastes the last cell's output. A step is done only when that output has been pasted.
- Commit and push from the work PC. Colab never commits.
- Every number in the report comes from a notebook output that was pasted back, or from a committed table, with its notebook and commit noted.

## Rules that do not bend
- **Data:** never commit data. TCB prices and anything that contains them (panel, features, forecasts, alert lists, models) stay on Drive. Committed tables hold rates and summaries only.
- **Raw files:** never edit them. They are copied once into `raw/` and listed in `raw/MANIFEST.csv`.
- **Missing prices:** a blank or zero price is "not reported". It is never imputed in a target; inputs may carry the last reported price forward. A missing driver stays empty, never 0. No ±inf.
- **The 2022 gap** (2022-03-12 to 2022-12-31): never filled across, never scored.
- **Real jumps:** never removed.
- **Availability dates:** every driver joins on its availability date. Weather is usable 5 days after the day it describes. The exchange rate is the last value on or before the report date. A value older than 7 days is left empty.
- **Choices** of model, level, threshold and window are made on 2024 only. They are written down and committed before 2025-26 is scored. 2025-26 was already looked at by the earlier run, so its results are labelled retrospective.
- **The baseline:** every accuracy figure is shown next to the "tomorrow = today" figure. If a model does not beat it, the report says so.
- **Wording:** a rise above the range is "not explained by measured cost drivers". Never "hoarding", "syndicate", "collusion", "cartel" or "manipulation". Alerts are abnormal-rise detection, not early warning. Drivers are "associated with", never "cause".
- **Changes:** any change to items, dates, drivers, method, threshold or source goes into `DEVIATIONS.md` before you continue. Scope changes need the user's approval.
- **Ask first** before anything destructive or externally visible: deleting files, `git reset --hard`, force-push, publishing, a public dashboard.
- **Downloads:** never download from TCB or any blocked or credentialed site yourself. If a file is missing, say exactly which file to put in Drive `raw/`.
- **Author:** `TO_CONFIRM`; put no name in any output until the user gives one.

## Stop and ask when
- A check fails twice after honest fixes.
- A result strongly contradicts expectations (report it; do not tune until it fits).
- A data error turns up, or a date, unit or item can only be resolved by guessing.
