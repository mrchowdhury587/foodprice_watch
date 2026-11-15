"""S24 Single-model design check on the real features (idempotent). Output: outputs/24_model/checks.json.
One LightGBM for all items and horizons; this stage fits it once at the first test origin and records sizes, timings and the leakage numbers.
No test-period target is used: the fit at cutoff 808 only sees rows whose target date is <= 808."""
import sys, json, time
sys.path.insert(0, "src")
import numpy as np, pandas as pd
from fpw.io import panel, ROOT
from fpw.project import PCFG, features_path, need
from fpw.checkpoint import sha256
from fpw import ml, state
state.start("S24")
F = pd.read_parquet(features_path())
S = ml.prepare(F); L = ml.stack(S); cols = ml.feature_columns()
first = int(PCFG["test"]["first_cutoff"])
tr = ml.train_rows(L, first)
assert tr.target_idx.max() <= first and tr.y.notna().all(), "a training target lies after the cutoff or is missing"
assert not (tr.touch_gap | tr.tgap).any(), "a training row touches the 2022 gap"
assert sorted(L.horizon.unique()) == list(PCFG["horizons"])
t0 = time.time(); model = ml.fit(L, first, cols); fit_s = time.time() - t0
O = ml.origin_rows(L, first); pred = model.predict(O[cols])
fc = ml.to_forecast(O, pred, "lgbm")
assert np.isfinite(fc.pred).all() and np.isfinite(fc.forecast).all()
imp = pd.Series(model.feature_importance("gain"), index=cols).sort_values(ascending=False)
chk = dict(rows_prepared=len(S), items=int(S.item_id.nunique()), rows_stacked=len(L), horizons=sorted(int(h) for h in L.horizon.unique()),
           n_features=len(cols), features=cols, first_test_cutoff=first, train_rows_at_first_cutoff=len(tr), train_rows_per_horizon={int(h): int((tr.horizon == h).sum()) for h in sorted(tr.horizon.unique())},
           max_training_target_idx=int(tr.target_idx.max()), origin_items=int(O.item_id.nunique()), forecasts_at_first_origin=len(fc),
           fit_seconds=round(fit_s, 2), objective=ml.PARAMS["objective"], n_estimators=ml.N_ESTIMATORS, top_gain_features=imp.head(8).round(1).to_dict(),
           input_file=features_path().name, input_sha256=sha256(features_path()))
(ROOT / "outputs/24_model").mkdir(parents=True, exist_ok=True)
(ROOT / "outputs/24_model/checks.json").write_text(json.dumps(chk, indent=2, default=str))
print("S24 unit: single model"); print(json.dumps({k: v for k, v in chk.items() if k != "features"}, indent=1, default=str))
