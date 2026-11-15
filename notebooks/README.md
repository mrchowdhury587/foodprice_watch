# Colab notebooks

| Notebook | Stages | What | Status |
|---|---|---|---|
| [01_data_features](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/01_data_features.ipynb) | S00, S22, S23 | Intake, extended panel and audit, features | ready |
| [02_model_selection_tuning](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/02_model_selection_tuning.ipynb) | S24, S25, S26 | One-model design, six-candidate selection on 2024, Optuna tuning, pre-registration | not built |
| [03_test_evaluation](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/03_test_evaluation.ipynb) | S27 | Sealed test (once) and full evaluation | not built |
| [04_alerts_explanation](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/04_alerts_explanation.ipynb) | S28, S29 | Ranges, alerts, SHAP explanation | not built |
| [05_production_export](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/05_production_export.ipynb) | S30, S32 | Production fit, exports, update run | not built |

Every notebook starts with the same four setup cells (mount Drive, clone GitHub `main` and install packages, set paths, run `make check`), then one stage cell driven by `STAGE`.
- Code comes from GitHub `main`, cloned into `/content/foodprice_watch` every session.
- Google Drive (`MyDrive/FoodPriceWatch`, set through `FPW_ARTIFACT_ROOT`) holds data, outputs, models and stage state only.
- Run the cells top to bottom, set `STAGE`, run the stage cell and the summary cell, paste the summary back, stop.
