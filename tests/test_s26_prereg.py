"""S26/S27 acceptance: the pre-registration is deterministic and fixes everything that must not change after the test is seen."""
import yaml
from fpw import prereg
from fpw.project import PCFG

SEL = dict(winner="lgbm", rule="lowest mean log-change MAE", scores={"lgbm": 0.01, "naive": 0.02})
TUN = dict(params=dict(objective="l1", num_leaves=15, learning_rate=0.05), n_estimators=200, rule="default kept")


def test_prereg_is_deterministic_and_complete():
    a, b = prereg.s27(SEL, TUN), prereg.s27(SEL, TUN)
    assert a == b
    d = yaml.safe_load(a)
    assert d["test"]["origins"] == 87 and d["test"]["first_cutoff"] == 808 and d["horizons"] == [1, 7, 14, 30]
    assert d["model"]["params"]["num_leaves"] == 15 and d["model"]["n_estimators"] == 200 and "horizon" in d["features"]
    assert d["metrics"]["primary"].startswith("mae_log") and d["schemes"]["random_or_stratified_kfold"] == "never"


def test_prereg_changes_when_the_tuned_setting_changes():
    assert prereg.s27(SEL, TUN) != prereg.s27(SEL, dict(TUN, n_estimators=300))


def test_alert_prereg_never_uses_events():
    d = yaml.safe_load(prereg.s28(dict(level=0.975, rule="r", fa_by_level={"0.975": 1.9})))
    assert d["events_used_for_threshold"] is False and d["model_trained_on_events"] is False and d["persistence"] == PCFG["alerts"]["persistence"]


def test_prereg_records_the_decision_when_lgbm_was_not_the_validation_winner():
    from fpw import prereg
    sel = dict(winner="ets", rule="r", scores={"lgbm": 0.0241, "ets": 0.0235, "naive": 0.0231}, naive_mae_log=0.0231)
    tun = dict(params={"objective": "l1"}, n_estimators=100, rule="t")
    assert "kept as the main model by user decision" in prereg.s27(sel, tun)
