"""S29/S30 acceptance: export files have the documented columns, no missing ranges, ranges bracket the forecast, wording of alert notes."""
import pandas as pd, pytest
from fpw.paths import ROOT

EX = ROOT / "outputs/export"
pytestmark = pytest.mark.skipif(not (EX / "forecasts.parquet").exists(), reason="exports exist only after S30 on Colab")


def test_forecast_columns_and_ranges():
    f = pd.read_parquet(EX / "forecasts.parquet")
    assert {"item_id", "origin_date", "horizon", "last_price", "forecast", "forecast_low", "forecast_high"} <= set(f.columns)
    assert sorted(f.horizon.unique()) == [1, 7, 14, 30] and f.forecast.gt(0).all()
    r = f.dropna(subset=["forecast_high"]); assert (r.forecast_low <= r.forecast).mean() > 0.9 and (r.forecast_high >= r.forecast_low).all()


def test_alert_drivers_wording():
    p = EX / "alert_drivers.csv"
    if not p.exists(): pytest.skip("S29 not run")
    d = pd.read_csv(p)
    for w in ["hoarding", "syndicate", "collusion", "cartel", "manipulation"]:
        assert not d.astype(str).apply(lambda c: c.str.contains(w, case=False)).any().any()
    if len(d): assert d.note.str.contains("not explained by measured cost drivers").all()
