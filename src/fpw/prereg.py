"""Pre-registration files. Built by deterministic functions (no timestamps, no commit hashes) so the copy committed to the repo can be
regenerated from the small tuning record and compared byte for byte with the copy the Colab run wrote to Drive."""
import yaml
from .project import PCFG
from . import ml


def _dump(doc):
    return yaml.safe_dump(doc, sort_keys=True, default_flow_style=False, allow_unicode=True, width=120)


def s27(selection, tuning):
    """What is fixed before the 2025-26 test period is scored once (SPEC.md evaluation protocol)."""
    t = PCFG["test"]
    doc = dict(
        stage="S27",
        purpose="Fixed before the 2025-26 test period is scored. The test is unsealed once; nothing below changes after seeing a test number.",
        model=dict(kind="one LightGBM for all items and horizons (horizon stacking)", selected_by=selection["rule"],
                   validation_scores=selection["scores"], winner=selection["winner"], objective=tuning["params"]["objective"],
                   params=tuning["params"], n_estimators=int(tuning["n_estimators"]), tuning_rule=tuning["rule"],
                   decision=("LightGBM kept as the main model by user decision 2026-11-16 although validation winner was %s (naive reference %.4f; LightGBM %.4f)"
                             % (selection["winner"], selection["naive_mae_log"], selection["scores"]["lgbm"])) if selection["winner"] != "lgbm" else "validation winner"),
        features=ml.feature_columns(), horizons=list(PCFG["horizons"]),
        test=dict(period=list(t["period"]), first_cutoff=int(t["first_cutoff"]), last_cutoff=int(t["last_cutoff"]), step=int(t["step"]),
                  origins=len(range(int(t["first_cutoff"]), int(t["last_cutoff"]) + 1, int(t["step"]))),
                  window="expanding", refit_every_n_cutoffs=int(t["refit_every_n_cutoffs"])),
        metrics=dict(primary="mae_log (mean absolute error of the log price change, about the percentage error)",
                     also=["mae_tk", "rmse_tk", "mape", "mase", "relative error to tomorrow=today (geometric mean over items)", "bias",
                           "direction accuracy on days the price moved", "error on change days vs unchanged days", "r2 on price changes"]),
        schemes=dict(main="rolling origin, expanding window, 2025-01..2026-10 (87 origins)", walk_forward_years=[2023, "2024 (labelled: tuning year)", "2025-26"],
                     sliding_window_reports=500, random_or_stratified_kfold="never"),
        error_analysis=["by item group", "by item", "by horizon", "Ramadan/Eid vs normal months", "rising vs falling periods", "before/after mid-2024",
                        "actual vs forecast plots", "error distribution", "bias over time", "worst-20 forecasts", "learning curve",
                        "Diebold-Mariano vs tomorrow=today (supporting only)"],
        limitation_to_state="The 2025-26 period was already scored by the earlier model, so this is not a first look. If the model does not beat tomorrow=today, that is reported.",
    )
    return _dump(doc)


def s28(threshold):
    """Alert settings fixed from 2024 non-event periods before any event is scored (never tuned on the 12 shock episodes)."""
    a = PCFG["alerts"]
    doc = dict(stage="S28", purpose="Fixed before any shock episode is scored.", chosen_level=float(threshold["level"]), horizon=int(a["horizon"]), window=int(a["window"]),
               min_obs=int(a["min_obs"]), persistence=dict(a["persistence"]), false_alarm_target_per_item_year=float(a["fa_target_per_item_year"]),
               threshold_rule=threshold["rule"], threshold_period=["2024-01-01", "2024-12-31"], false_alarms_per_item_year_by_level=threshold["fa_by_level"],
               event_window_days=dict(a["event_window_days"]), events_used_for_threshold=False, model_trained_on_events=False)
    return _dump(doc)


def s34(alert_level):
    """TCB price-rise reference fixed before any alert is scored against it (S34). The rule uses reported TCB prices only; no news, no forecast bound."""
    r = PCFG["rises"]
    doc = dict(stage="S34", purpose="Fixed before alerts are scored against TCB price rises. Nothing below changes after seeing a result.",
               rise_rule=dict(formula="R = P_t / P_(t-w) - 1 on reported prices of one item", window_reports=int(r["window_reports"]), threshold=float(r["threshold"]),
                              persist_reports=int(r["persist_reports"]), merge_gap_reports=int(r["merge_gap_reports"]),
                              excluded="windows touching the sparse 2022 period; days without a reported price"),
               matching=dict(before_reports=int(r["match"]["before_reports"]), after_reports=int(r["match"]["after_reports"]),
                             unit="one alert run (first day of an uninterrupted alert) against one rise episode, one-to-one, same item"),
               alerts=dict(source="state/prereg_S28.yaml (unchanged)", chosen_level=float(alert_level)),
               sensitivity_thresholds=[float(x) for x in r["sensitivity"]], sensitivity_use="reported only, never used to choose the rule",
               validation_period=list(r["validation"]), retrospective_period=list(r["retrospective"]),
               retrospective_note="2025-26 was already scored by the earlier model, so results there are retrospective, not a first look",
               placebo=dict(draws=int(r["placebo_draws"]), seed=42, method="alert-run dates of each item shifted by a random whole number of report days"),
               tuned_on_shock_episodes=False, news_used=False, model_retrained=False)
    return _dump(doc)


def verify_s27(repo_path, drive_path, selection, tuning):
    """The committed pre-registration, the copy S26 wrote to Drive and a fresh rebuild from the tuning record must be byte-identical."""
    a, b = repo_path.read_text(encoding="utf-8"), drive_path.read_text(encoding="utf-8")
    assert a == b == s27(selection, tuning), "pre-registration differs between the repo, Drive and the tuning record: do not score the test"
