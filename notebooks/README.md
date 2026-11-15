# Colab workflow

- [01_data_features.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/01_data_features.ipynb): Intake, panel, audit and features
- [02_model_training.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/02_model_training.ipynb): Model implementation, selection and tuning
- [03_evaluation.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/03_evaluation.ipynb): Sealed testing, ranges, alerts and explanations
- [04_production.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/04_production.ipynb): Production exports, dashboard and updates
- [05_results_documentation.ipynb](https://colab.research.google.com/github/mrchowdhury587/foodprice_watch/blob/main/notebooks/05_results_documentation.ipynb): Results, limitations and documentation

Every workflow notebook starts with two code cells: mount Drive, then clone the repository if missing or pull updates if it already exists. Code, data and persistent artifacts live under MyDrive/FoodPriceWatch. Package installation, checks and stage execution follow in separate sections. Existing nonempty folders without Git and conflicting Git changes require review; no files are reset. Notebooks 01-05 initialize their own runtime, mount Drive, install packages and run startup checks. After reconnecting, initialize the selected notebook again. All notebooks share Drive state. Stop after each stage and paste output for review. Notebooks 02-05 mark unfinished stages explicitly; they do not train or score models. Report writing follows verified, registered results.
