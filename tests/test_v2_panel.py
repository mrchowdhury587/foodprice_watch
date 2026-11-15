"""S22: the extended panel. Part 1 runs anywhere on a small made-up file; part 2 runs where the real panel exists (Drive)."""
import json
from pathlib import Path
import pytest
pd = pytest.importorskip("pandas"); np = pytest.importorskip("numpy")
import yaml
from fpw import panel as P
from fpw.paths import ROOT as R, CODE_ROOT
PC = yaml.safe_load((CODE_ROOT / "config/project.yaml").read_text(encoding="utf-8"))
OUT = R / "data/processed" / PC["panel_file"]
RAWP = R / "data/raw/project"

# ---------- part 1: logic on a made-up file
def raw_frame():
    rows = []
    for d, potato, onion in [("2022-03-10", 20, 30), ("2022-03-11", 20, 32), ("2022-06-01", None, 40), ("2023-01-02", 22, 40), ("2023-01-03", 22, 41)]:
        for prod, v in [("Potato", potato), ("Onion", onion)]:
            rows.append(dict(Date=d, Product=prod, Unit="per kg", Price_Min=None if v is None else v - 1, Price_Max=None if v is None else v + 1,
                             Price_Avg=v, Week_Ago_Min=None))
    df = pd.DataFrame(rows); df["Date"] = pd.to_datetime(df.Date)
    for c in ["Price_Min", "Price_Max", "Price_Avg", "Week_Ago_Min"]: df[c] = df[c].astype(float)
    return df
META = pd.DataFrame(dict(item_id=["Potato | per kg", "Onion | per kg"], eval_stratum=["veg", "veg"], stratum=["veg", "veg"], short_history=[False, False]))
GAP = ["2022-03-12", "2022-12-31"]
def test_build_report_index_gap_and_missing():
    df = P.build(raw_frame(), META, {(pd.Timestamp("2023-01-02"), "Onion | per kg")}, GAP)
    assert list(df.columns[:3]) == ["Date", "Product", "Unit"] and len(df) == 10 and not df.duplicated(["Date", "item_id"]).any()
    po = df[df.item_id == "Potato | per kg"]
    assert list(po.report_idx) == [0, 1, 2, 3, 4]                         # report days, not calendar days
    assert list(po.gap_2022) == [False, False, True, False, False]
    assert po.Price_Avg.isna().sum() == 1 and not po.is_reported.iloc[2]  # not reported stays empty, never filled
    assert list(po.reports_since_change.fillna(-1)) == [0, 1, -1, 0, 1]
    assert df.flag_audit_candidate.sum() == 1
def test_build_rejects_unknown_item():
    df = raw_frame(); df.loc[0, "Product"] = "Mango"
    with pytest.raises(AssertionError): P.build(df, META, set(), GAP)
def test_same_as_base_detects_any_change():
    new = raw_frame(); base = new[new.Date <= "2023-01-02"].copy(); cols = ["Price_Min", "Price_Max", "Price_Avg", "Week_Ago_Min"]
    assert P.same_as_base(new, base, "2023-01-02", cols) == 0             # adding a later day is fine
    changed = new.copy(); changed.loc[0, "Price_Max"] += 1
    assert P.same_as_base(changed, base, "2023-01-02", cols) == 1         # an earlier value changed
    filled = new.copy(); filled.loc[filled.Price_Avg.isna(), "Price_Avg"] = 21.0
    assert P.same_as_base(filled, base, "2023-01-02", cols) == 1          # a not-reported price was filled
    assert P.same_as_base(new[new.Date != "2022-03-11"], base, "2023-01-02", cols) > 0   # an earlier day went missing

# ---------- part 2: the real extended panel
real = pytest.mark.skipif(not OUT.exists(), reason="S22 not run here (data lives on Drive)")
@pytest.fixture(scope="module")
def df(): return pd.read_parquet(OUT)
@real
def test_invariants(df):
    assert df.item_id.nunique() == 63 and not df.duplicated(["Date", "item_id"]).any()
    b = df.Price_Min.notna() & df.Price_Max.notna()
    assert np.isclose(df.Price_Avg[b], (df.Price_Min[b] + df.Price_Max[b]) / 2).all() and not (df.Price_Min > df.Price_Max).any()
    assert not (df[["Price_Min", "Price_Max", "Price_Avg"]] <= 0).any().any()
    assert df.loc[df.gap_2022, "Date"].nunique() == 24
    assert json.loads((R / "outputs/22_panel/checks.json").read_text())["week_ago_match_share"] >= 0.995
@real
def test_longer_than_base_and_same_before(df):
    last = pd.Timestamp(PC["base_last_date"])
    assert df.Date.min() == pd.Timestamp("2021-05-17") and df.Date.max() >= last   # equal while the base file is the price file
    old = df[df.Date <= last]
    assert len(old) == 76440 and old.Date.nunique() == 1412 and old.report_idx.max() == 1411
    base = pd.read_csv(RAWP / "tcb_dhaka_daily_prices_2021_2026.csv", parse_dates=["Date"]); base["item_id"] = base.Product + " | " + base.Unit
    m = old.merge(base, on=["Date", "item_id"], suffixes=("", "_base"))
    assert len(m) == 76440
    for c in ["Price_Min", "Price_Max", "Price_Avg"]:
        assert ((m[c].isna() & m[c + "_base"].isna()) | np.isclose(m[c].fillna(0), m[c + "_base"].fillna(0))).all(), c
@real
def test_same_as_earlier_panel_where_it_exists(df):
    v1 = R / "data/processed" / PC["base_panel_file"]
    if not v1.exists(): pytest.skip("earlier panel not on this machine")
    a = pd.read_parquet(v1).sort_values(["item_id", "Date"]).reset_index(drop=True)
    b = df[df.Date <= PC["base_last_date"]].sort_values(["item_id", "Date"]).reset_index(drop=True)
    assert len(a) == len(b) and (a.item_id.values == b.item_id.values).all() and (a.report_idx.values == b.report_idx.values).all()
    for c in ["Price_Avg", "reports_since_change", "days_since_prev_report"]:
        assert np.allclose(a[c].fillna(-1).values, b[c].fillna(-1).values), c
    for c in ["gap_2022", "short_history", "flag_audit_candidate", "eval_stratum"]:
        assert (a[c].values == b[c].values).all(), c
@real
def test_corrections_still_in_place(df):
    assert df.loc[(df.item_id == "MS Rod (40 Grade) | per metric ton") & (df.Date == "2021-06-19"), "Price_Max"].iloc[0] == 70500
    assert df.loc[(df.item_id == "Palm Olein - Bottled | 5 litre") & (df.Date == "2025-04-18"), "Price_Avg"].isna().all()
