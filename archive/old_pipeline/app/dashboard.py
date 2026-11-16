"""Local dashboard. Reads the three export files (forecasts.parquet, alerts.csv, alert_drivers.csv) from a folder.
    pip install streamlit pandas pyarrow matplotlib
    streamlit run app/dashboard.py -- "G:/My Drive/FoodPriceWatch/outputs/export"
Runs on this computer only. The files hold TCB prices: do not publish them or the dashboard."""
import sys
from pathlib import Path
import pandas as pd, streamlit as st

folder = Path(sys.argv[-1]) if len(sys.argv) > 1 and Path(sys.argv[-1]).is_dir() else Path("outputs/export")
st.set_page_config(page_title="Food Price Watch", layout="wide")
st.title("Bangladesh Food Price Watch")
st.caption("Forecasts and abnormal-rise alerts for TCB Dhaka retail prices. Alerts detect a rise above the expected range; they are not an early warning.")
need = [folder / n for n in ("forecasts.parquet", "alerts.csv", "alert_drivers.csv")]
if not all(p.exists() for p in need):
    st.error(f"Missing export files in {folder}. Run notebook 05 (stage S30) first."); st.stop()
fc = pd.read_parquet(need[0]); al = pd.read_csv(need[1], parse_dates=["tdate"]); dr = pd.read_csv(need[2])
tab1, tab2, tab3 = st.tabs(["Forecasts", "Alerts", "Why an alert"])
with tab1:
    item = st.selectbox("Item", sorted(fc.item_id.unique()))
    d = fc[fc.item_id == item].sort_values("horizon")
    st.write(f"Last reported price on {d.origin_date.max():%Y-%m-%d}: **{d.last_price.iloc[0]:.1f} Tk**")
    d = d.assign(horizon=d.horizon.astype(str) + " report days")
    st.dataframe(d[["horizon", "forecast", "forecast_low", "forecast_high"]].round(1), hide_index=True)
    st.bar_chart(d.set_index("horizon")[["forecast_low", "forecast", "forecast_high"]])
    st.caption(f"Range: central {fc.range_level.iloc[0]:.0%}-level bounds from the item's recent forecast errors.")
with tab2:
    only = st.checkbox("Only items in the most recent 30 days", True)
    a = al[al.tdate >= al.tdate.max() - pd.Timedelta(days=30)] if only else al
    st.write(f"{len(a)} alert starts"); st.dataframe(a.sort_values("tdate", ascending=False).round(3), hide_index=True)
with tab3:
    if dr.empty: st.write("No alerts.")
    else:
        dr["label"] = dr.item_id + " | " + dr.tdate.astype(str); pick = st.selectbox("Alert day", dr.label.iloc[::-1])
        r = dr[dr.label == pick].iloc[0]; groups = [c for c in dr.columns if c in ("price_history", "calendar", "weather", "onion_export_measures", "exchange_rate")]
        st.bar_chart(r[groups].astype(float)); st.write(f"Expected change (log): {r.expected_change_log:.3f}. Price change above the expected range (log): {r.resid:.3f}.")
        st.info(r.note)
