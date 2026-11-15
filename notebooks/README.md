# Colab notebook

[run_stage.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/run_stage.ipynb) runs one stage (S00, S22, S23 today; later stages are added to the same notebook as they are implemented).

How it works:
- Code comes from GitHub `main`, cloned into `/content/foodprice_watch` every session.
- Google Drive (`MyDrive/FoodPriceWatch`) holds data, outputs, models and stage state only. Set through `FPW_ARTIFACT_ROOT`.
- Run the cells top to bottom, set `STAGE`, run the stage cell, paste the printed summary back, stop.
