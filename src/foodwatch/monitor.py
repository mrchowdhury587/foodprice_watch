"""Monitor (notebook 07 and app/monitor_app.py): a day-by-day replay of the three abnormal-rise alert rules on TCB prices.
Abnormal-rise detection, not early warning. Everything shown for a day uses only what was known on that day: the range of
target day t is built from forecast errors whose targets are on or before the forecast origin t-7 (see foodwatch.alerts)."""
import numpy as np
import pandas as pd

from foodwatch import alerts as al, behaviour as bh

RULES = {"A": "ML range (LightGBM)", "B": "simple range (tomorrow = today)", "C": "fixed 7-report rise"}
RULE_KEY = {v: k for k, v in RULES.items()}
COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}   # same fixed slots as the report figures (validated palette)
INK, MUTED, GRID, BAND = "#0b0b0b", "#898781", "#e1e0d9", "#f3e3c3"
PERIODS = {"2024 validation": ("2024-01-01", "2024-12-31"), "2025-26 retrospective": ("2025-01-01", "2026-10-24")}


def episodes(D, settings):
    r = settings["rises"]
    return bh.episodes(bh.rise_days(D, r["window_reports"]), r["threshold"], r["persist_reports"], r["merge_gap_reports"])


def build(F7, D, settings, choice):
    """One row per item and report day with a 7-day forecast: price, 7-report change and, per rule, the upper bound in Tk,
    whether the price was above it, the alert flag (3 of the last 5 days) and the start of each alert run."""
    a = settings["alerts"]; hz, k, m = a["horizon"], a["persistence"]["k"], a["persistence"]["m"]
    lvA, lvB, thC = choice["A"]["setting"], choice["B"]["setting"], choice["C"]["setting"]
    PA = al.bounds(al.table(F7, "lgbm", hz), hz, [lvA], a["window"], a["min_obs"])
    PB = al.bounds(al.table(F7, "naive", hz), hz, [lvB], a["window"], a["min_obs"])
    assert (PA[["item_id", "target_idx"]].values == PB[["item_id", "target_idx"]].values).all(), "A and B rows differ"
    exA, onA = al.range_alerts(PA, lvA, k, m)
    exB, onB = al.range_alerts(PB, lvB, k, m)
    exC, onC = al.threshold_alerts(PB, thC, k, m)
    M = pd.DataFrame({"item_id": PB.item_id, "date": PB.tdate, "report_idx": PB.target_idx.astype(int),
                      "price": np.exp(PB.lp_origin + PB.y), "price_7_ago": np.exp(PB.lp_origin), "change_7": np.expm1(PB.y)})
    M["bound_A"] = np.exp(PA.lp_origin + PA.pred + PA[f"hi{lvA}"])
    M["bound_B"] = np.exp(PB.lp_origin + PB.pred + PB[f"hi{lvB}"])
    M["bound_C"] = np.exp(PB.lp_origin) * (1 + thC)
    for r, ex, on in (("A", exA, onA), ("B", exB, onB), ("C", exC, onC)):
        M[f"exceed_{r}"] = ex.fillna(False).astype(bool).values
        M[f"alert_{r}"] = on.fillna(False).astype(bool).values
        M[f"days_above_{r}"] = M.groupby("item_id")[f"exceed_{r}"].transform(lambda s: s.astype(int).rolling(m, min_periods=1).sum()).astype(int)
        prev = M.groupby("item_id")[f"alert_{r}"].shift(1, fill_value=False).astype(bool)
        M[f"run_start_{r}"] = M[f"alert_{r}"] & ~prev
    M = M[M.date.notna() & M.price.notna()].copy()   # the last origins' targets lie after the last report day
    EP = episodes(D, settings)
    M["in_rise"] = False
    for _, e in EP.iterrows():
        M.loc[(M.item_id == e.item_id) & M.report_idx.between(e.onset_idx, e.end_idx), "in_rise"] = True
    return M.reset_index(drop=True), EP


def report_days(M):
    return sorted(M.date.dt.strftime("%Y-%m-%d").unique())


def short(item_id):
    return item_id.split(" | ")[0]


def status_on(M, day, rule):
    """Status of every item on a day (the last report day on or before it), under one rule."""
    day = pd.Timestamp(day)
    d = M[M.date <= day].sort_values("date").groupby("item_id").tail(1)
    rows = []
    for _, x in d.iterrows():
        h = M[(M.item_id == x.item_id) & (M.date <= x.date)]
        since = h[h[f"run_start_{rule}"]].date.max() if x[f"alert_{rule}"] else pd.NaT
        b = x[f"bound_{rule}"]
        if x[f"alert_{rule}"]:
            st = "ALERT: abnormal rise"
        elif not np.isfinite(b):
            st = "no range yet"
        elif x[f"days_above_{rule}"] > 0:
            st = f"above range on {x[f'days_above_{rule}']} of the last 5 days"
        else:
            st = "normal"
        rows.append({"Item": short(x.item_id), "Unit": x.item_id.split(" | ")[1], "Report day": x.date.strftime("%Y-%m-%d"),
                     "Price (Tk)": round(x.price, 2), "Change over 7 reports (%)": round(100 * x.change_7, 1),
                     ("Threshold (Tk)" if rule == "C" else "Upper bound (Tk)"): round(b, 2) if np.isfinite(b) else None,
                     "Status": st, "Alert since": since.strftime("%Y-%m-%d") if pd.notna(since) else ""})
    order = {"ALERT: abnormal rise": 0}
    return pd.DataFrame(rows).sort_values("Status", key=lambda s: s.map(lambda v: order.get(v, 1 if v.startswith("above") else 2))).reset_index(drop=True)


def _runs(M, rule):
    r = M[M[f"run_start_{rule}"]][["item_id", "report_idx", "date"]].rename(columns={"report_idx": "start_idx", "date": "start_date"})
    ends = []
    for _, x in r.iterrows():
        h = M[(M.item_id == x.item_id) & (M.report_idx >= x.start_idx)]
        off = h[~h[f"alert_{rule}"]]
        ends.append(off.date.iloc[0] if len(off) else pd.NaT)
    return r.assign(end_date=ends).reset_index(drop=True)


def alert_log(M, EP, settings, rules, item="all", period="all"):
    """Every alert run: start, length, price and change at the start, and (hindsight) whether it matched a sustained rise.
    Matching is done within each period, exactly as in notebook 05b; runs before 2024 are not scored."""
    before, after = settings["alerts"]["match"]["before_reports"], settings["alerts"]["match"]["after_reports"]
    out = []
    for rule in rules:
        rn = _runs(M, rule)
        rn["matched"] = "not scored (before 2024)"
        rn["period"] = ""
        for pname, per in PERIODS.items():
            sel = rn.start_date.between(pd.Timestamp(per[0]), pd.Timestamp(per[1]))
            eps = al.in_period(EP, "onset_date", per)
            _, r2 = al.match(rn[sel][["item_id", "start_idx", "start_date"]], eps, before, after)
            rn.loc[sel, "matched"] = np.where(r2.matched.values, "yes", "no")
            rn.loc[sel, "period"] = pname
        st = M.set_index(["item_id", "report_idx"])
        idx = list(zip(rn.item_id, rn.start_idx))
        rn["price_at_start"] = st.loc[idx, "price"].round(2).values if len(rn) else []
        rn["change_7_pct"] = (100 * st.loc[idx, "change_7"]).round(1).values if len(rn) else []
        rn["rule"] = RULES[rule]
        out.append(rn)
    L = pd.concat(out, ignore_index=True)
    if item != "all":
        L = L[L.item_id.map(short) == item]
    if period != "all":
        L = L[L.period == period]
    L = L.assign(item=L.item_id.map(short), start=L.start_date.dt.strftime("%Y-%m-%d"),
                 end=L.end_date.dt.strftime("%Y-%m-%d").fillna("still on"))
    cols = ["rule", "item", "start", "end", "price_at_start", "change_7_pct", "period", "matched"]
    return L.sort_values("start", ascending=False)[cols].rename(columns={
        "price_at_start": "Price at start (Tk)", "change_7_pct": "Change over 7 reports (%)",
        "matched": "Matched a sustained rise (hindsight)"}).reset_index(drop=True)


def item_chart(M, EP, item, rules, start, end):
    """Price, the upper bound of each chosen rule, shaded sustained rises (hindsight) and alert-run starts."""
    import matplotlib.pyplot as plt
    import matplotlib.transforms as mt
    it = [i for i in M.item_id.unique() if short(i) == item][0]
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    d = M[(M.item_id == it) & M.date.between(s, e)]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for _, x in EP[(EP.item_id == it) & (pd.to_datetime(EP.end_date) >= s) & (pd.to_datetime(EP.onset_date) <= e)].iterrows():
        ax.axvspan(max(pd.to_datetime(x.onset_date), s), min(pd.to_datetime(x.end_date), e), color=BAND, linewidth=0)
    ax.plot(d.date, d.price, color=INK, linewidth=1.3, label="price")
    tr = mt.blended_transform_factory(ax.transData, ax.transAxes)
    for j, r in enumerate(rules):
        ax.step(d.date, d[f"bound_{r}"], where="post", color=COLOR[r], linewidth=1, alpha=0.9,
                label=("threshold: " if r == "C" else "upper bound: ") + RULES[r])
        st = d[d[f"run_start_{r}"]]
        ax.scatter(st.date, [1.03 + 0.05 * j] * len(st), marker="v", s=40, color=COLOR[r], transform=tr, clip_on=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelcolor="#52514e")
    ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    ax.set_ylabel(f"Tk {it.split(' | ')[1]}", color="#52514e")
    ax.set_title(f"{item}: shaded = sustained 10 % rise (hindsight); triangles = start of an alert run", fontsize=10, color=INK, loc="left",
                 pad=10 + 14 * len(rules))
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


def checks(M, alerts_file, R5, settings, choice):
    """Notebook 07 checks: alerts equal 05b; exceed equals price above bound; run counts equal R5."""
    A = alerts_file.pivot_table(index=["item_id", "target_idx"], columns="rule", values="alert", aggfunc="first")
    j = M.set_index(["item_id", "report_idx"])
    out = {"alerts_equal_05b": bool(all((A.loc[j.index, r].astype(bool).values == j[f"alert_{r}"].values).all() for r in "ABC"))}
    ok = True
    for r in "AB":
        b = j[f"bound_{r}"]; f = b.notna()
        lhs = np.log(j.price[f]) - np.log(b[f])
        clear = lhs.abs() > 1e-9
        ok &= bool(((lhs[clear] > 0) == j[f"exceed_{r}"][f][clear]).all())
    out["exceed_equals_price_above_bound"] = ok
    th = choice["C"]["setting"]
    out["exceed_C_equals_change"] = bool(((j.change_7 >= th - 1e-12) == j.exceed_C).all())
    runs = {}
    for r in "ABC":
        rn = _runs(M, r)
        for pname, per in PERIODS.items():
            runs[(pname, r)] = int(rn.start_date.between(pd.Timestamp(per[0]), pd.Timestamp(per[1])).sum())
    rr = R5.assign(key=list(zip(R5.period, R5.rule.map({"ML range": "A", "simple range": "B", "fixed 7-report rise": "C"}))))
    out["runs_equal_R5"] = bool(all(runs[k_] == n for k_, n in zip(rr.key, rr.alert_runs)))
    out["rows"] = int(len(M)); out["first_day"] = str(M.date.min().date()); out["last_day"] = str(M.date.max().date())
    out["ok"] = all(v for k_, v in out.items() if isinstance(v, bool))
    return out
