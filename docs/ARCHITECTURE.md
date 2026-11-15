# Architecture

Two places, never mixed: **code** (GitHub, cloned fresh each session) and **artifacts** (Google Drive: data, outputs, models, state).
`src/fpw/paths.py` exposes both: `CODE_ROOT` (the checkout) and `ROOT` (`FPW_ARTIFACT_ROOT`; the checkout itself on the work PC).

```
inbox/ (you drop files on Drive)
   | S00 intake: copy + SHA-256 (data/raw/MANIFEST.csv)
   v
data/raw/            read-only inputs (never edited)
   | S22 extended panel + audit      S23 features (kept drivers, availability-dated, has_<slot> flags)
   v
data/processed/      tcb_v2_rebuilt.parquet, features_v2.parquet
   | S24 single model -> S25 selection (2024) -> S26 tuning -> S27 pre-register + test once
   | S28 ranges and alerts -> S29 SHAP -> S30 production -> S31 dashboard, S32 update, S33 docs   (S24+ not built yet)
   v
outputs/, models/, reports/project/   every number in RESULTS_REGISTER.md (value, file, command, commit)
```

## Layers
| Layer | Where | Rule |
|---|---|---|
| Settings | `config/project.yaml` (`config.yaml` is frozen) | the only place for dates, horizons, thresholds |
| Library | `src/fpw/` | importable, no side effects on import beyond reading config |
| Stage scripts | `src/stages/` | one script per step; units written atomically with a `_SUCCESS.json` marker |
| Registry | `src/fpw/registry.py` | what each stage runs, produces and is tested by |
| Ledger | `state/stages.json` | status and hashes only; entries are never deleted or reordered |
| Tests | `tests/` | acceptance checks per stage plus seal, wording and notebook-guard tests |
| Archive | `archive/` | earlier comparison study, kept as the record; never imported |

## `src/fpw/` modules
`paths` (roots) · `io` (raw loaders) · `project` (reads `config/project.yaml`) · `panel` (v2 panel) · `features` (v2 features) ·
`drivers` (exchange rate, weather, events) · `checkpoint` (sha256, unit markers, one-shot test seal) · `state` (ledger) ·
`registry`, `runner` (`make stage S=S22`) · `check` (`make check`).

## Running
- Colab: `notebooks/01_data_features.ipynb`. Work PC: `make check`, `make stage S=S22 [DRY=1]` (use `.venv`).
- The runner refuses to start a stage before its dependencies are done and never makes git commits.
