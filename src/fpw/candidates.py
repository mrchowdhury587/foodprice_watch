"""S25 model candidates behind one interface: fit_fn(L, cutoff, cols) -> object with .predict(DataFrame of stacked origin rows).

naive  'tomorrow = today' (predicted change 0)
ets    classical AutoETS on each item's own past (statsforecast), refitted at every origin
ridge  linear model on the same features (one-hot item, stratum and horizon)
rf     random forest on the same features
lgbm   the single LightGBM of fpw.ml
lstm   small sequence model on the last 30 daily changes plus the same statics (torch, CPU)

Every candidate is trained only on rows with target date <= cutoff (ml.train_rows) and returns the common forecast table of ml.to_forecast.
"""
import numpy as np, pandas as pd
from . import ml

ORDER = ["naive", "ridge", "ets", "rf", "lgbm", "lstm"]           # simplest first: the tie rule prefers the earlier one
CATEGORICAL = ["item_code", "stratum_code", "horizon"]
WINDOW = 30


class Naive:
    def predict(self, X): return np.zeros(len(X))


def fit_naive(L, cutoff, cols): return Naive()


class _Sk:
    def __init__(self, model, cols): self.model, self.cols = model, cols
    def predict(self, X): return self.model.predict(X[self.cols])


def fit_ridge(L, cutoff, cols, alpha=10.0):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    tr = ml.train_rows(L, cutoff)
    num = [c for c in cols if c not in CATEGORICAL]; cat = [c for c in cols if c in CATEGORICAL]
    pre = ColumnTransformer([("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    m = Pipeline([("pre", pre), ("ridge", Ridge(alpha=alpha))]).fit(tr[cols], tr["y"])
    return _Sk(m, cols)


def fit_rf(L, cutoff, cols, n_estimators=100):
    from sklearn.ensemble import RandomForestRegressor
    tr = ml.train_rows(L, cutoff)
    m = RandomForestRegressor(n_estimators=n_estimators, min_samples_leaf=50, max_features=0.5, max_samples=0.3, n_jobs=-1, random_state=42)
    m.fit(tr[cols].fillna(-999), tr["y"])
    class _Rf(_Sk):
        def predict(self, X): return self.model.predict(X[self.cols].fillna(-999))
    return _Rf(m, cols)


def fit_lgbm(L, cutoff, cols, params=None, n_estimators=None):
    return ml.fit(L, cutoff, cols, params, n_estimators)


def windows(S, width=WINDOW):
    """The last `width` one-report log changes of each row's item (row j-1 is the day before); NaN -> 0 (no change observed)."""
    W = np.column_stack([ml._at(S, "r1", -j) for j in range(width)])
    return np.nan_to_num(W, nan=0.0)


class LstmPred:
    def __init__(self, net, mu, sd, win, statics, n_items, horizons):
        self.net, self.mu, self.sd, self.win, self.statics, self.horizons = net, mu, sd, win, statics, horizons

    def _x(self, X, idx):
        import torch
        w = torch.tensor(self.win[idx] / self.sd[0], dtype=torch.float32).unsqueeze(-1)
        s = (X[self.statics].fillna(0).values - self.mu) / self.sd[1]
        hz = np.stack([(X.horizon.values == h).astype(float) for h in self.horizons], axis=1)
        return w, torch.tensor(np.hstack([s, hz]), dtype=torch.float32), torch.tensor(X.item_code.values, dtype=torch.long)

    def predict(self, X):
        import torch
        self.net.eval()
        with torch.no_grad():
            w, s, it = self._x(X, X.index.values)
            return self.net(w, s, it).numpy()


def make_fit_lstm(S, epochs=8, hidden=32, seed=42):
    """Returns fit_fn for the LSTM. The window array is built once from S and tiled to the stacked table (blocks are in horizon order)."""
    win_S = windows(S)
    horizons = ml.settings()["horizons"]
    statics = [c for c in ["dev30", "vol30", "rsc", "month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", "holiday_next7"] if c in S.columns]

    def fit_fn(L, cutoff, cols):
        import torch, torch.nn as nn
        torch.manual_seed(seed); np.random.seed(seed); torch.set_num_threads(2)
        win = np.tile(win_S, (len(horizons), 1))
        tr = ml.train_rows(L, cutoff)
        n_items = int(L.item_code.max()) + 1
        st = tr[statics].fillna(0).values
        mu, sd_s = st.mean(0), st.std(0) + 1e-6
        sd = (float(win[tr.index.values].std() + 1e-6), sd_s)
        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = nn.Embedding(n_items, 8); self.lstm = nn.LSTM(1, hidden, batch_first=True)
                self.head = nn.Sequential(nn.Linear(hidden + 8 + len(statics) + len(horizons), 32), nn.ReLU(), nn.Linear(32, 1))
            def forward(self, w, s, it):
                _, (h, _) = self.lstm(w)
                return self.head(torch.cat([h[-1], self.emb(it), s], dim=1)).squeeze(-1)
        net = Net()
        p = LstmPred(net, mu, sd, win, statics, n_items, horizons)
        w, s, it = p._x(tr, tr.index.values); y = torch.tensor(tr["y"].values, dtype=torch.float32)
        opt = torch.optim.Adam(net.parameters(), lr=2e-3); n = len(y)
        for _ in range(epochs):
            net.train(); perm = torch.randperm(n)
            for i in range(0, n, 1024):
                b = perm[i:i + 1024]; opt.zero_grad()
                loss = (net(w[b], s[b], it[b]) - y[b]).abs().mean(); loss.backward(); opt.step()
        return p
    return fit_fn


ETS_MIN_OBS = 30


def ets_forecasts(S, cutoffs, horizons=None, model_name="ets"):
    """AutoETS on each item's own carried log price, refitted at every origin (an ETS model is its own recent history). Origins use only rows <= cutoff."""
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS
    horizons = horizons or ml.settings()["horizons"]; H = max(horizons); out = []
    for c in cutoffs:
        hist = S[(S.report_idx <= c) & S.lp.notna() & ~S.gap_2022].sort_values(["item_id", "report_idx"])
        Y = hist[["item_id", "lp"]].rename(columns={"item_id": "unique_id", "lp": "y"}); Y["ds"] = Y.groupby("unique_id").cumcount() + 1
        n = Y.groupby("unique_id").ds.max()
        Y = Y[Y.unique_id.map(n) >= ETS_MIN_OBS]                      # AutoETS refuses tiny series; those items get "no change" (naive) below
        f = (StatsForecast(models=[AutoETS(season_length=1)], freq=1, n_jobs=-1).forecast(df=Y[["unique_id", "ds", "y"]], h=H).reset_index() if len(Y)
             else pd.DataFrame(dict(unique_id=[], ds=[], AutoETS=[])))
        f["step"] = f.ds - f.unique_id.map(n)
        origin = S[(S.report_idx == c) & S.lp.notna() & ~S.touch_gap].set_index("item_id")
        for h in horizons:
            fh = f[f.step == h].set_index("unique_id")["AutoETS"]
            O = origin.reset_index()
            O = O.assign(horizon=h, y=O[f"y{h}"], target_idx=O.report_idx + h)
            pred = O.item_id.map(fh).values - O.lp.values
            out.append(ml.to_forecast(O, np.where(np.isnan(pred), 0.0, pred), model_name).assign(fit_cutoff=c))
    return pd.concat(out, ignore_index=True)


def fit_fn_for(name, S, params=None, n_estimators=None):
    if name == "naive": return fit_naive
    if name == "ridge": return fit_ridge
    if name == "rf": return fit_rf
    if name == "lgbm": return lambda L, c, cols: fit_lgbm(L, c, cols, params, n_estimators)
    if name == "lstm": return make_fit_lstm(S)
    raise ValueError(name)


def run_candidate(name, S, L, cols, cutoffs, refit_every=8, params=None, n_estimators=None):
    """Forecast table of one candidate over the given origins."""
    if name == "ets":
        return ets_forecasts(S, cutoffs)
    return ml.forecasts(L, cutoffs, cols, refit_every=refit_every, model_name=name, fit_fn=fit_fn_for(name, S, params, n_estimators))


def choose_winner(scores, margin, order=ORDER, exclude=("naive",)):
    """scores: {model: validation error, lower is better}. The best model wins unless a simpler one (earlier in `order`) is within
    `margin` (relative) of the best: then the simpler one wins. 'Tomorrow = today' is the reference, never the chosen model."""
    cand = {m: v for m, v in scores.items() if m not in exclude and np.isfinite(v)}
    best = min(cand, key=cand.get)
    close = [m for m in cand if cand[m] <= cand[best] * (1 + margin)]
    return sorted(close, key=order.index)[0]
