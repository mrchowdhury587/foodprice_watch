<!-- CLAUDE.md -->
@AGENTS.md

## Git commits
- Never add Claude as co-author or add any attribution line (Co-Authored-By, Claude-Session, "Generated with") to commit messages or PR descriptions.
- Commit, then push to origin main. Never commit data (TCB price files stay out of git).

## Colab
- Always use the Google account mhpcoder (Chrome account index authuser=1, so every Colab URL ends in ?authuser=1; verify the account shown at the top right before running anything).
- Notebook links follow this pattern: https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/01_data_intake.ipynb?authuser=1 (replace the notebook name).
- Drive folder: MyDrive/FoodPriceWatch_v2 of that account holds this project's data and outputs. The old folder MyDrive/FoodPriceWatch is shared from the mehedi11908015 account and added to mhpcoder's My Drive as a shortcut; it is only the source of the raw files and of the old panel for the regression check. Code is cloned from GitHub main; Drive holds data only.

## Local runs (since 2026-11-17)
- Colab cannot mount Google Drive for mhpcoder ("credential propagation was unsuccessful"). Until it works, notebooks run locally on the work PC against `E:\msc_project\FoodPriceWatch_v2_local` (same layout as the Drive folder: `raw/`, `processed/`, `reports/`), with `FW_DATA_ROOT` set to that folder. It is outside the repo; never copy its files into git.
- Run a notebook locally by executing its code cells after the three setup cells, with `CODE_COMMIT` = the pushed commit + " (local run, work PC)". Log each run in `reports/RUN_LOG.md` as a LOCAL run and add a DEVIATIONS row. Copy only the rates/summary tables into `reports/tables/`.
- When Drive mounts again, copy the new `processed/` and `reports/figures/` files to `MyDrive/FoodPriceWatch_v2` and rerun the notebooks in Colab.

## Report
- Overleaf project: https://www.overleaf.com/project/6afa6515e99d9136ba743329
