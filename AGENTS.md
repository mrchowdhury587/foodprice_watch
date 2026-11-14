# AGENTS.md — Bangladesh Food Price Watch

## What this is
A master's PROJECT (not a thesis): a price prediction system. For each TCB item it forecasts the price 1, 7, 14 and 30 report days ahead with an expected range, raises an alert when the price stays above the range, and attaches a driver breakdown to each alert. Comparisons appear only as a validation step and in limitations. The agent produces verified results; the human writes the report later from reports/ and reports/RESULTS_REGISTER.md. Scope and "done" live in SPEC.md. The current plan is docs/PROJECT_PLAN_2026-11-15.md (newer than SPEC.md where they differ; each difference is logged in DEVIATIONS.md). Machine state lives in state/stages.json. Narrative state lives in PROGRESS.md.

## Two tracks
- Earlier design (stages S00-S11, run 2026-11-11): the five-question comparison study. Its scripts, outputs, pre-registrations and seals are kept as they are and are never overwritten.
- Prediction system (stages S22-S33): new scripts, new output files (`*_v2`, `reports/project/`), settings in `config/project.yaml`.

## Commands
- Check everything: `make check`    (stages.json vs disk markers, tests/)
- Run one stage:     `make stage S=NN` (idempotent; skips finished units)
- Dry run:           `make stage S=NN DRY=1`

## Two run modes
- Direct mode: you can execute in the Colab runtime. Run commands yourself.
- Human-runner mode: you cannot execute there (or the user prefers it). Emit ONE notebook cell per unit, ending with a printed summary (unit id, rows, sha256, check result). Wait for the user to paste the output. Update stages.json and PROGRESS.md only from pasted output. If no output was pasted, the unit is not done.
- Work PC (user decision 2026-11-15): pip is allowed inside the repo's `.venv` only. Use it for data collection (convert, append, audit), unit tests on small made-up frames and the local dashboard. Heavy work (model fits, tuning, the test) runs in Colab. `fpw.paths`, `fpw.runner`, `fpw.state` and `tools/tcb_download.py`, `tools/tcb_append.py` stay standard library only.

## Startup ritual (every session, before any new work)
1. Confirm the Drive root from config.yaml is mounted; work only inside it.
2. Read, in order: this file, SPEC.md, docs/PROJECT_PLAN_2026-11-15.md, DECISIONS.md, the last 2 PROGRESS.md entries, DEVIATIONS.md, state/stages.json, then `git log --oneline -20` and `git status`.
3. Delete *.tmp files under outputs/ and data/ (leftovers from a dropped session).
4. Run `make check`. It re-hashes every done stage's outputs against its _SUCCESS.json. If a check fails, set that stage to pending, log why, and do not pass it.
5. A stage marked in_progress is not trusted: keep only units with a valid _SUCCESS.json and resume at the next unit.
6. Pick the first stage whose status is not done/skipped and whose depends_on are all done or skipped. If it needs a PENDING decision, a setting marked TO_CONFIRM in config/project.yaml, or missing data, stop and ask.
7. Work on that one stage only. Stop after it, show what changed, and wait for the user's OK.

## End-of-unit / end-of-stage ritual
- After each unit: atomic write, then its _SUCCESS.json marker. Commit at least every 30 minutes or every 20 units.
- After the stage: run its SPEC.md acceptance checks → update stages.json (status, output_sha256, git_commit, finished_at) → append PROGRESS.md → commit "SNN: <summary> [checks pass]" → stop and report.

## Rules that do not bend
- Never edit data/raw/. Corrections go to corrections_proposed.csv and need my approval. The extended price file arrives under a new name (config/project.yaml `price_file`).
- Never download from TCB, DAM or any blocked or credentialed site yourself. If a source is missing, mark the stage blocked and tell me exactly what file to drop into inbox/.
- Never fabricate, simulate or impute data unless SPEC.md says that stage does so. Blank or zero price = not reported; never imputed in targets (inputs may carry the last reported price forward). Missing drivers stay empty with a has_<slot> flag, never 0. Never fill prices across the 2022 gap and never score it. Never remove real jumps.
- Every driver joins on its true availability date; never use a driver value before its publication date (weather + 5 days; exchange rate as of the last value on or before the report date). No ±inf anywhere.
- Every number in reports/ must come from a committed script and be listed in reports/RESULTS_REGISTER.md (value, file, command, commit). If you did not run it, say so.
- Never overwrite data/raw/project/baseline_results_by_group.csv or any earlier result; write new versions alongside.
- Do not edit config.yaml (the old run's unit markers record its hash). New settings go in config/project.yaml.
- Choose models, settings, windows and thresholds on validation data only (2024). Test seal: the 2025-01..2026-10 test period may be scored only after the stage's pre-registration is committed, and only once per stage. src/fpw/checkpoint.py enforces it. Never tune on the test. If the model does not beat "tomorrow = today", say so in limitations.
- One main model for all items and horizons; other models appear only in the model-selection step. Keep every method explainable by the student.
- Alert thresholds are fixed from 2024 non-event false-alarm rates before any event scoring. Never tune them on the 12 shock episodes. The model is never trained on events.
- Wording: residual rises are "not explained by measured cost drivers". Never "hoarding", "syndicate", "collusion", "cartel" or "manipulation". Alerts are abnormal-rise detection, not early warning. Kept drivers are "helpful for specific items", not proven.
- Author: use config.yaml author. If it is TO_CONFIRM, put no name in any output.
- Any change to sample, items, dates, horizon, method, threshold or source goes into DEVIATIONS.md, with the reason, before you continue. Scope changes need my approval.
- Do not delete, edit or reorder entries in stages.json; update only their status fields. New stages are appended at the end.
- Ask before anything destructive or externally visible: rm -rf, git reset --hard, force-push, publishing (GitHub, Zenodo, arXiv), a public dashboard, any API key or account. Exports and models contain TCB prices: keep them out of git.

## Stop and ask when
- A needed decision is PENDING, a setting is TO_CONFIRM, or a needed file is MISSING in MANIFEST.csv.
- An acceptance check fails twice after honest fixes.
- A result strongly contradicts expectations (report it; do not tune until it fits).
- Baseline reproduction differs beyond tolerance.
- You find a data error not listed in SPEC.md §Data rules.
- A date, unit or market classification can only be resolved by guessing.

## Session-end report format
Done (check command and result) · Not done · Blocked (why, and what you need from me) · Deviations logged · Numbers I am unsure of · Next stage/unit.
