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
        outputs=["state/selection_S25.json", "reports/project/tables/P5_selection.csv", "reports/project/tables/P5_selection_overall.csv"],
        tests=["tests/test_ml_design.py", "tests/test_s25_select.py"]),
}
