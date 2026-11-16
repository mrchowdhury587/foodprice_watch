"""S27 acceptance on made-up data: the seal allows exactly one unsealing of a committed pre-registration; evaluation tables and the register behave."""
import subprocess, numpy as np, pandas as pd, pytest
from fpw import checkpoint, ml, metrics as M, evaluate as E, register
from test_ml_design import made_up


def git(cwd, *a): return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@example.com"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "prereg.yaml").write_text("a: 1\n"); monkeypatch.chdir(tmp_path); return tmp_path


def test_seal_needs_a_committed_prereg_and_allows_one_unsealing(repo):
    seals = repo / "seals"
    with pytest.raises(RuntimeError, match="committed"):
        checkpoint.unseal_test("S27", repo / "prereg.yaml", seal_dir=seals)
    git(repo, "add", "prereg.yaml"); git(repo, "commit", "-qm", "prereg")
    assert checkpoint.unseal_test("S27", repo / "prereg.yaml", seal_dir=seals) == "unsealed"
    assert checkpoint.unseal_test("S27", repo / "prereg.yaml", seal_dir=seals) == "resumed"          # same plan: a dropped session does not count twice
    (repo / "prereg.yaml").write_text("a: 2\n"); git(repo, "commit", "-qam", "changed")
    with pytest.raises(RuntimeError, match="already unsealed"):
        checkpoint.unseal_test("S27", repo / "prereg.yaml", seal_dir=seals)


@pytest.fixture(scope="module")
def tables():
    pytest.importorskip("lightgbm")
    S = ml.prepare(made_up()); L = ml.stack(S)
    fc = ml.forecasts(L, list(range(100, 130, 5)), ml.feature_columns(), refit_every=3, params=dict(num_threads=1), n_estimators=15)
    dates = pd.Series(pd.date_range("2023-01-01", periods=150), index=range(150))
    cal = pd.DataFrame(dict(in_ramadan=0, days_to_eid_fitr=50, days_to_eid_adha=80), index=range(150)); cal.loc[100:110, "in_ramadan"] = 1
    return S, L, fc, dates, cal, S[["item_id", "eval_stratum"]].drop_duplicates()


def test_tables_have_one_row_per_horizon_and_relative_error(tables):
    S, L, fc, dates, cal, strata = tables
    H = E.by_horizon(fc, strata)
    assert sorted(H.horizon) == [1, 7, 14, 30] and {"mae_log", "gmean_rel_mae", "direction_acc", "r2_changes", "bias_tk"} <= set(H.columns)
    G = E.by_group(fc, strata); assert set(G.eval_stratum) == set(strata.eval_stratum)
    I = E.by_item(fc, M.mase_scale(L, 100)); assert {"mase", "naive_scale"} <= set(I.columns) and I.item_id.nunique() == 3


def test_error_analysis_splits_and_worst_list(tables):
    S, L, fc, dates, cal, strata = tables
    t = E.tag(fc, dates, cal); EA = E.error_analysis(t)
    assert set(EA.split) == {"ramadan_or_eid", "direction", "era", "month"} and "ramadan/eid window" in set(EA.level)
    w = E.worst(t, 5); assert len(w) == 5 and w.abs_err_log.is_monotonic_decreasing
    assert len(E.bias_over_time(t)) > 0


def test_learning_curve_and_figures(tables, tmp_path):
    S, L, fc, dates, cal, strata = tables
    cur = E.learning_curve(L, 120, ml.feature_columns(), dict(num_threads=1), 15)
    assert len(cur) == 15 and {"train_l1", "holdout_l1"} <= set(cur.columns)
    t = E.tag(fc, dates, cal)
    paths = E.figures(t, E.by_horizon(fc, strata), cur, E.bias_over_time(t), tmp_path)
    assert len(paths) >= 4 and all(p.exists() and p.stat().st_size > 1000 for p in paths)


def test_register_section_is_replaced_not_duplicated(tmp_path, monkeypatch):
    monkeypatch.setattr(register, "REGISTER", tmp_path / "RESULTS_REGISTER.md")
    monkeypatch.setattr(register, "CODE_ROOT", tmp_path); (tmp_path / "reports/project").mkdir(parents=True); (tmp_path / "reports/project/RESULTS_REGISTER.md").write_text("# Register\n")
    register.section("S27", "S27 test", "cmd", ["a.csv"], [("m1", 0.123456)]); register.section("S27", "S27 test", "cmd", ["a.csv"], [("m1", 0.5)])
    t = (tmp_path / "RESULTS_REGISTER.md").read_text()
    assert t.count("<!-- S27 -->") == 1 and "0.5" in t and "0.1235" not in t
