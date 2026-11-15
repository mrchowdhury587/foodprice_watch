"""Stage registry: the one place that says what each stage runs, produces and is tested by.

Used by src/stages/finalize.py (acceptance) and fpw.runner (`make stage S=NN`).
state/stages.json stays the ledger (status, hashes); this file is code, not state.
Commands run from the project root. The earlier comparison-study stages (S01, S04-S11) live in archive/.
"""
PY = "python -W ignore"

STAGES = {
    "S00": dict(
        run=["python src/stages/s00_intake.py"], commit="S00: scaffold and intake",
        outputs=["data/raw/MANIFEST.csv", "DECISIONS.md"], tests=["tests/test_s00.py"]),
    # ---- prediction-system track (docs/PROJECT_PLAN_2026-11-15.md); settings in config/project.yaml
    "S22": dict(
        run=[f"{PY} src/stages/s22_panel.py"], note="extended price file, audit table P2_audit.csv made on the work PC by tools/tcb_audit.py",
        outputs=["data/processed/tcb_v2_rebuilt.parquet", "outputs/22_panel/checks.json", "reports/project/tables/P2_panel_summary.csv",
                 "reports/project/tables/P2_audit.csv", "reports/project/tables/P2_audit_summary.csv"],
        tests=["tests/test_v2_panel.py", "tests/test_wording.py"]),
    "S23": dict(
        run=[f"{PY} src/stages/s23_features.py"],
        outputs=["data/processed/features_v2.parquet", "outputs/23_features/checks.json", "reports/project/tables/P3_driver_inventory.csv"],
        tests=["tests/test_v2_features.py", "tests/test_wording.py"]),
    "S24": dict(
        run=[f"{PY} src/stages/s24_model.py"],
        outputs=["outputs/24_model/checks.json"], tests=["tests/test_ml_design.py"]),
    "S25": dict(
        run=[f"{PY} src/stages/s25_select.py"],
        outputs=["state/selection_S25.json", "reports/project/tables/P5_model_selection.csv", "reports/project/tables/P5_model_selection_overall.csv"],
        tests=["tests/test_ml_design.py", "tests/test_s25_select.py"]),
    "S26": dict(
        run=[f"{PY} src/stages/s26_tune.py"],
        outputs=["reports/project/tables/P6_tuning_trials.csv", "state/tuning_S26.json", "state/prereg_S27.yaml"],
        tests=["tests/test_ml_design.py", "tests/test_s26_prereg.py"]),
    "S27": dict(
        run=[f"{PY} src/stages/s27_test.py"], note="sealed test scored once, prereg_S27.yaml committed first",
        outputs=["state/prereg_S27.yaml"] + [f"reports/project/tables/P7_{n}.csv" for n in ["accuracy_by_horizon", "accuracy_by_group", "accuracy_by_item", "walk_forward", "error_analysis", "worst20", "dm_vs_naive", "learning_curve", "bias_over_time"]]
                + ["reports/project/figures/F10_relative_error_by_horizon.png", "reports/project/RESULTS_REGISTER.md"],
        tests=["tests/test_s26_prereg.py", "tests/test_s27_eval.py", "tests/test_wording.py"]),
    "S28": dict(
        run=[f"{PY} src/stages/s28_alerts.py"], note="alert level fixed from 2024 non-event periods, prereg_S28.yaml committed first, 12 shock episodes scored once",
        outputs=["state/prereg_S28.yaml", "outputs/28_alerts/forecasts_daily.parquet", "outputs/28_alerts/alerts.csv"]
                + [f"reports/project/tables/P8_{n}.csv" for n in ["event_scores", "level_curve", "range_quality", "range_quality_by_period", "alert_summary"]],
        tests=["tests/test_s28_alerts.py", "tests/test_wording.py"]),
    "S29": dict(
        run=[f"{PY} src/stages/s29_explain.py"],
        outputs=["outputs/export/alert_drivers.csv"] + [f"reports/project/tables/P9_{n}.csv" for n in ["driver_overall", "driver_by_horizon", "driver_by_item_group", "driver_by_item", "sign_checks", "driver_stability"]],
        tests=["tests/test_exports.py", "tests/test_wording.py"]),
    "S30": dict(
        run=[f"{PY} src/stages/s30_export.py"], note="exports and model hold TCB prices: Drive only",
        outputs=["outputs/export/forecasts.parquet", "outputs/export/alerts.csv", "models/lgbm_production.txt"],
        tests=["tests/test_exports.py"]),
}
