<!-- PROGRESS.md â€” append-only; newest entry at the bottom -->

## 2026-11-11 19:10 — stage S00 — finalized (local, human-assisted intake)
- Verified: pytest tests/test_s00.py -> pass; MANIFEST 41 present / 0 missing
- Note: intake 2026-11-11: 41 present, 0 missing (32 project + 9 external); S02 blocked (original TCB Excel files not supplied)
- Note: wti_daily_datahub.csv came from the user's chat output New_datasets_2026-10-26.zip; external files (WFP, AgriPriceBD, Pink Sheet, OHLC) from the user's chat uploads. A 29 Oct results pack (S01, S04-S07, S09-S11 done) exists outside this repo and is NOT yet re-verified here.

## 2026-11-11 â€” Colab run on Drive (ledger copy: reports/RUN_LEDGER_2026-11-11.json)
- S00, S01, S04, S05, S06, S07, S09, S10, S11 finalized on Drive (2026-11-11 13:25 to 16:11 UTC); each stage test passed. S05 needed REPRO_EXPLAINED.md (see DEVIATIONS). S02 blocked, S03 and S08 pending (no code), S99 pending.
- Results copied into reports/ and state/ from the Drive backup; the local state/stages.json is intentionally not overwritten (a local make check would reset stages whose data/ outputs exist only on Drive).
- Report draft: reports/thesis/main.tex.

## 2026-11-15 - new plan adopted (docs/PROJECT_PLAN_2026-11-15.md), step A
- Project reframed as a prediction system; stages S22-S33 appended to state/stages.json; settings in config/project.yaml; AGENTS.md, SPEC.md, DECISIONS.md (D13-D17), DEVIATIONS.md updated; repo URL fixed in README.md and the Colab notebook.
- Not done: step 1 code (commit d8f67f0 was never pushed; waiting for step1_data_collection.patch from the user).
- Colab note: DECISIONS.md is one of the S00 hashed outputs, so after pulling, re-run the S00 cell once (it re-finalizes S00) before any new stage.

## 2026-11-15 - step 1 rebuilt on branch v2/step-1 (data collection tools)
- The patch for commit d8f67f0 was not found on the work PC; tools/tcb_convert.py taken from Downloads/BD_Food_Price_Watch.zip (wrapper added), tools/tcb_append.py extended, docs/DATA_COLLECTION.md and tests/test_tools_append.py added.
- Verified on the work PC: re-translation of all 76,440 rows gives 0 Product/Unit mismatches; base cut at 2026-09-30 plus converter output to 2026-10-24 rebuilds the base file byte for byte; conversion is repeatable.
- Seen, not yet used: the folder now converts to 1,430 report days (18 new, 2026-10-25 to 2026-11-12, 60 rows each, all names translated). Three of the new dates are a Friday or Saturday (10-30, 10-31, 11-06): to be checked in S22 before the extended file is accepted.

## 2026-11-15 - step 2 (S22) code and work-PC part, branch v2/step-2
- Extended price file built on the work PC: 77,520 rows, 1,430 report days to 2026-11-12 (sha256 0159e1f4...); earlier rows byte-identical to the base file. The Friday/Saturday dates among the new days are genuine: TCB reports seven days a week and each file heading names its date (serials 265-282).
- Audit (tools/tcb_audit.py): 1,530 of 1,530 sampled rows checked against the original Excel files, 0 mismatches; the 5 ginger candidates equal the originals (kept, still flagged). Three planted errors were all found.
- s22_panel.py tested on a scratch copy with the real files: all invariants pass. NOT yet run on Drive: S22 stays pending until the Colab output is pasted.

## 2026-11-15 - S22 checked in a fresh Colab session (new notebook, local storage, no Drive)
- Data: the 32 project files + the extended price file sent from the work PC (bundle sha256 b9a7a418...). Code: main at 9fcfc66.
- S00 intake: 33 present (9 external sources missing, as before). S01: 76,440 rows, 1,412 report days, 7 tests passed. S22: 77,520 rows, 1,430 report days to 2026-11-12, 0 cells differing from the base file, 8 tests passed (including equality with the earlier panel).
- Bug found by this run and fixed: the S22 note contained a semicolon, so the unquoted finalize command was split by the shell and the runner printed a false STOP after S22 was already accepted. Note reworded; tests/test_registry.py now rejects shell characters in notes.
- This was a verification run in a temporary session. The Drive ledger is unchanged: S22 is still pending there.

## 2026-11-15 - handover resumed in Desktop checkout
- Copied docs/HANDOVER_2026-11-15.md from C:/Users/mrcho/foodprice_watch; fetched origin. Local main and origin/main are 0de0cfe; origin/v2/step-3 is fac8962, still awaiting merge approval.
- Startup check reset local S00 to pending: data/raw/MANIFEST.csv is absent and DECISIONS.md differs from the stored hash. This checkout has no mounted Drive or pipeline data. No Colab stage completion is claimed.
- Verification: python -m fpw.check using the existing repo virtual environment: CHECK PASS, 22 passed, 26 skipped (data-dependent checks skipped). Initial sandbox run had pytest temporary-directory permission errors; rerun outside sandbox passed, with a pytest cache permission warning.
- Next: user approval of feature branch merge; Drive S00 intake refresh and S22 verified output, then S23. Heavy model work remains in Colab.
## 2026-11-15 - step 3 (S23) code, branch v2/step-3
- src/fpw/features.py + src/stages/s23_features.py: features_v2.parquet with calendar, weather (2024 choice), onion export measure, exchange rate. Earlier S04 untouched.
- Work-PC run on a scratch copy with the real files: 77,520 rows; tests pass, including re-derived weather (+5 d) and exchange-rate values and equality of every kept column with the earlier features.parquet up to 2026-10-24.
- Found: the onion export flag is unknown after 2025-03-27 (end of the events table); weather empty after 2026-10-31, exchange rate after 2026-11-01. Logged in DEVIATIONS.md.

## 2026-11-15 - approved S23 local merge
- User approved continuing and merging v2/step-3; merged origin/v2/step-3 into local main at ed7ee32, preserving local handover and S00 pending status. Not pushed.
- Post-merge python -m fpw.check: CHECK PASS, 28 passed, 31 skipped, one pytest cache permission warning. Data-dependent verification remains unavailable locally.
- Prepared docs/COLAB_RESUME_S00.py as one human-runner intake cell. Not executed in Colab; no stage completion inferred. Await its pasted output before proceeding to S22.
