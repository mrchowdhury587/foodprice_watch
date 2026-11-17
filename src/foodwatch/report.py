"""Notebook 06: thesis tables (R1-R7), figures (F3-F5) and the results register, built only from finished outputs.
Nothing here fits, chooses or tunes anything."""
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

RULES = {"A": "ML range", "B": "simple range", "C": "fixed 7-report rise"}
MODELS = {"lgbm": "LightGBM", "ets": "ETS", "naive": "tomorrow = today"}
# categorical slots 1-3 of the dataviz reference palette (validated: CVD and normal-vision separation pass); fixed per entity
COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "lgbm": "#2a78d6", "ets": "#eb6834"}
INK, MUTED, GRID, BAND = "#0b0b0b", "#898781", "#e1e0d9", "#f3e3c3"
NOTEBOOK = {"D": "02_data_processing", "B": "03_price_behaviour", "M1": "04a_forecast_choice", "M2": "04a_forecast_choice",
            "M3": "04b_forecast_test", "M4": "04b_forecast_test", "A1": "05a_alert_choice"}
SOURCES = ["D1_panel_summary", "B1_change_frequency", "B2_change_size", "B3_unchanged_runs", "B5_rise_episodes_by_item_year", "B6_ramadan",
           "M2_validation_models", "M3_test_accuracy", "M4_test_by_item", "A2_rule_comparison", "A3_rule_overlap", "A4_range_coverage",
           "A5_alerts_by_item"]
RETRO = "2025-26 retrospective"


def notebook_of(name):
    for key in (name[:2], name[0]):
        if key in NOTEBOOK:
            return NOTEBOOK[key]
    return "05b_alert_scoring"


def short(item_id):
    return item_id.split(" | ")[0]


def unit(item_id):
    return item_id.split(" | ")[1]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()


def load_sources(repo):
    """Committed source tables, with the commit that last changed each. Fails if any has uncommitted changes."""
    T, commit = {}, {}
    for name in SOURCES:
        p = Path(repo) / "reports/tables" / f"{name}.csv"
        T[name] = pd.read_csv(p)
        assert git(repo, "status", "--porcelain", "--", str(p.relative_to(repo))) == "", f"{name} has uncommitted changes"
        commit[name] = git(repo, "log", "-1", "--format=%h", "--", str(p.relative_to(repo)))
    return T, commit


def _period(p):
    p = str(p)
    return RETRO if ("2025" in p or "retrospective" in p) else "2024 validation"


# ---------- tables ----------
def r1_data(T, items):
    D = T["D1_panel_summary"]
    drv = {i["id"]: ", ".join([n for n, f in (("weather", i["weather"]), ("exchange rate", i["fx"])) if f]) or "none" for i in items}
    return pd.DataFrame({"item": D.item_id.map(short), "unit": D.item_id.map(unit), "group": D.group, "first_day": D.first_date,
                         "last_day": D.last_date, "report_days": D.report_days, "pct_not_reported": 100 * D.share_not_reported,
                         "pct_unchanged": 100 * D.share_unchanged, "drivers": D.item_id.map(drv)})


def r2_behaviour(T):
    B1 = T["B1_change_frequency"].assign(n_changed=lambda d: d.share_changed * d.report_days)
    allyrs = 100 * B1[B1.year.astype(str) == "all"].set_index("item_id").share_changed
    B1 = B1[B1.year.astype(str) != "all"].astype({"year": int})
    def share(d):
        g = d.groupby("item_id")[["n_changed", "report_days"]].sum()
        return 100 * g.n_changed / g.report_days
    B2, B3 = T["B2_change_size"].set_index("item_id"), T["B3_unchanged_runs"].set_index("item_id")
    B5 = T["B5_rise_episodes_by_item_year"].groupby("item_id")[["episodes_7pct", "episodes_10pct", "episodes_15pct"]].sum()
    R = pd.DataFrame({"pct_days_changed_2021_26": allyrs, "pct_days_changed_2024_26": share(B1[B1.year >= 2024]),
                      "median_change_pct": B2.median_abs_pct, "p95_change_pct": B2.p95_abs_pct,
                      "median_unchanged_run": B3.median_days, "longest_unchanged_run": B3.longest_days,
                      "rises_7pct": B5.episodes_7pct, "rises_10pct": B5.episodes_10pct, "rises_15pct": B5.episodes_15pct})
    return R.reset_index().assign(item_id=lambda d: d.item_id.map(short)).rename(columns={"item_id": "item"})


def r3_ramadan(T):
    B = T["B6_ramadan"]
    return pd.DataFrame({"item": B.item_id.map(short), "ramadans": B.ramadans, "days_before_ramadan": B.days_before_ramadan,
                         "median_change_before_pct": B.median_change_before_ramadan_pct, "median_change_other_pct": B.median_change_other_days_pct,
                         "pct_rise_days_before": 100 * B.share_rise_days_before_ramadan, "pct_rise_days_other": 100 * B.share_rise_days_other})


def r4_forecast(T):
    parts = [T["M2_validation_models"].assign(period="2024 validation"), T["M3_test_accuracy"].assign(period=RETRO)]
    M = pd.concat(parts, ignore_index=True)
    M = M[M.model != "naive"]
    return pd.DataFrame({"period": M.period, "model": M.model.map(MODELS), "horizon": M.horizon, "mae_log": M.mae_log,
                         "mae_log_naive": M.mae_log_naive, "rel_mae_gmean": M.gmean_rel_mae, "accuracy": M.accuracy,
                         "accuracy_naive": M.accuracy_naive, "p_holm": M.p_holm}).reset_index(drop=True)


def r5_rules(T):
    A = T["A2_rule_comparison"].assign(period=lambda d: d.period.map(_period))
    return pd.DataFrame({"period": A.period, "rule": A.rule.map(RULES), "setting": A.setting, "episodes": A.episodes,
                         "caught": A.detected, "recall": A.recall, "recall_random_dates": A.placebo_recall, "p": A.placebo_p,
                         "alert_runs": A.alert_runs, "precision": A.precision, "median_delay_reports": A.median_delay_reports,
                         "unmatched_per_item_year": A.unmatched_per_item_year})


def r5b_overlap(T):
    return T["A3_rule_overlap"].assign(period=lambda d: d.period.map(_period)).rename(
        columns={"both": "caught_by_both", "A_only": "ML_range_only", "B_only": "simple_range_only", "neither": "caught_by_neither"})


def r6_focus(T):
    A5 = T["A5_alerts_by_item"].assign(period=lambda d: d.period.map(_period))
    A5["cell"] = np.where(A5.episodes == 0, "none (" + A5.alert_runs.astype(str) + ")",
                          A5.detected.astype(str) + "/" + A5.episodes.astype(str) + " (" + A5.alert_runs.astype(str) + ")")
    W = A5.pivot_table(index="item_id", columns=["period", "rule"], values="cell", aggfunc="first")
    W.columns = [f"{'2024' if p.startswith('2024') else '2025_26'}_{r}" for p, r in W.columns]
    M4 = T["M4_test_by_item"]
    rel = M4[M4.horizon == 7].pivot_table(index="item_id", columns="model", values="rel_mae")
    W["rel_mae_h7_lightgbm_2025_26"], W["rel_mae_h7_ets_2025_26"] = rel["lgbm"], rel["ets"]
    W = W.reset_index()
    W["note"] = np.where(A5.groupby("item_id").episodes.sum().reindex(W.item_id).values == 0, "no sustained rise: alerts cannot be judged", "")
    return W.assign(item_id=W.item_id.map(short)).rename(columns={"item_id": "item"})


def r7_coverage(T):
    A = T["A4_range_coverage"].assign(period=lambda d: d.period.map(_period))
    return pd.DataFrame({"period": A.period, "rule": A.rule.map(RULES), "days": A.n, "nominal": A.nominal, "coverage": A.coverage,
                         "kupiec_p": A.kupiec_p})


CAPTIONS = {
    "R1_data": "The eight items: TCB Dhaka daily retail prices, 17 May 2021 to 24 October 2026 (the sparse 2022 period is kept as not reported).",
    "R2_behaviour": "How often and how much prices move. Change sizes are on days the price changed; runs are in report days; sustained rises use the 14-report rule (10 % main, 7 % and 15 % sensitivity).",
    "R3_ramadan": "Changes in the 30 days before Ramadan against other days (descriptive: associated with the season; says nothing about why).",
    "R4_forecast": "Forecast benchmark: error of the 1- to 30-report-day log change next to tomorrow = today (geometric mean over items). Relative MAE above 1 means worse than tomorrow = today. 2025-26 is retrospective.",
    "R5_alert_rules": "Alert rules scored against sustained 10 % rises (abnormal-rise detection, not early warning). Settings fixed on 2024; 2025-26 is retrospective.",
    "R5b_rule_overlap": "Sustained rises caught by the ML range and the simple range.",
    "R6_focus_items": "Per item: rises caught / episodes (alert runs) for each rule, and relative MAE at 7 days in 2025-26 (retrospective).",
    "R7_range_coverage": "Share of days at or below the upper bound of the range against the nominal level; Kupiec test p.",
}


def build_all(T, items):
    return {"R1_data": r1_data(T, items), "R2_behaviour": r2_behaviour(T), "R3_ramadan": r3_ramadan(T), "R4_forecast": r4_forecast(T),
            "R5_alert_rules": r5_rules(T), "R5b_rule_overlap": r5b_overlap(T), "R6_focus_items": r6_focus(T),
            "R7_range_coverage": r7_coverage(T)}


def to_tex(df, path, caption, label):
    fmt = {c: (lambda x: f"{x:.3f}") if df[c].dtype.kind == "f" else None for c in df.columns}
    caption = caption.replace("%", r"\%").replace("_", r"\_")   # captions are not escaped by pandas
    tex = df.to_latex(index=False, escape=True, caption=caption, label=label, na_rep="",
                      formatters={c: f for c, f in fmt.items() if f}, column_format="l" * len(df.columns))
    Path(path).write_text(tex, encoding="utf-8", newline="\n")


# ---------- checks ----------
def trace_checks(T, R):
    """Every copied number equals its source value; derived totals equal their sources."""
    out = {}
    D, r1 = T["D1_panel_summary"], R["R1_data"]
    out["R1"] = bool(np.allclose(r1.pct_unchanged, 100 * D.share_unchanged) and (r1.report_days.values == D.report_days.values).all())
    out["R2"] = bool(R["R2_behaviour"].rises_10pct.sum() == T["B5_rise_episodes_by_item_year"].episodes_10pct.sum())
    out["R3"] = bool(np.allclose(R["R3_ramadan"].median_change_before_pct, T["B6_ramadan"].median_change_before_ramadan_pct))
    r4 = R["R4_forecast"]
    for nm, per in (("M2_validation_models", "2024 validation"), ("M3_test_accuracy", RETRO)):
        M = T[nm][T[nm].model != "naive"]
        out[f"R4_{nm[:2]}"] = bool(np.allclose(r4[r4.period == per].rel_mae_gmean.values, M.gmean_rel_mae.values))
    A2 = T["A2_rule_comparison"]
    out["R5"] = bool((R["R5_alert_rules"].caught.values == A2.detected.values).all() and np.allclose(R["R5_alert_rules"].recall, A2.recall))
    A5 = T["A5_alerts_by_item"]
    det = A5.groupby(["period", "rule"]).detected.sum().values
    out["R6"] = bool((det == A2.sort_values(["period", "rule"]).detected.values).all())
    out["R7"] = bool(np.allclose(R["R7_range_coverage"].coverage, T["A4_range_coverage"].coverage))
    return out


def retro_labelled(R):
    ok = True
    for df in R.values():
        if "period" in df:
            ok &= bool(df.period.map(lambda p: ("2025" not in p) or ("retrospective" in p)).all())
    return ok


def no_prices(R):
    return all(not any(c.lower().startswith("price") for c in df.columns) for df in R.values())


def wording_check(texts, forbidden):
    """Forbidden words in any generated text ("not early warning" is allowed: it is the required disclaimer)."""
    hits = []
    for t in texts:
        t2 = t.lower().replace("not early warning", "")
        for w in forbidden:
            if re.search(r"\b" + re.escape(w.lower()) + r"\b", t2):
                hits.append(w)
    return sorted(set(hits))


# ---------- figures ----------
def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelcolor="#52514e")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_forecast(r4, path):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    hs = sorted(r4.horizon.unique())
    for ax, per in zip(axes, ["2024 validation", RETRO]):
        d = r4[r4.period == per]
        ax.axhline(1, color=MUTED, linestyle="--", linewidth=1.2)
        ax.text(-0.25, 0.994, "tomorrow = today (1.0)", va="top", fontsize=8, color="#52514e")
        ends = {}
        for key, name in (("lgbm", "LightGBM"), ("ets", "ETS")):
            s = d[d.model == name].set_index("horizon").rel_mae_gmean.reindex(hs)
            ax.plot(range(len(hs)), s.values, color=COLOR[key], linewidth=2, marker="o", markersize=6)
            ends[name] = s.values[-1]
        hi_, lo_ = sorted(ends, key=ends.get, reverse=True)
        mid = (ends[hi_] + ends[lo_]) / 2
        ax.text(len(hs) - 1 + 0.15, max(ends[hi_], mid + 0.008), hi_, va="center", fontsize=8, color=INK)
        ax.text(len(hs) - 1 + 0.15, min(ends[lo_], mid - 0.008), lo_, va="center", fontsize=8, color=INK)
        ax.set_xticks(range(len(hs)), [f"{h}" for h in hs]); ax.set_xlim(-0.3, len(hs) - 0.2)
        ax.set_xlabel("horizon (report days)", color="#52514e"); ax.set_title(per, fontsize=10, color=INK, loc="left")
        _style(ax)
    axes[0].set_ylabel("relative MAE (above 1 = worse)", color="#52514e"); axes[0].set_ylim(0.975, None)
    fig.suptitle("No model beats tomorrow = today", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(); fig.savefig(path, dpi=200, facecolor="white"); plt.close(fig)


def fig_recall(r5, path):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.0), sharex=True)
    rules = list(RULES.values())
    for ax, per in zip(axes, ["2024 validation", RETRO]):
        d = r5[r5.period == per].set_index("rule").reindex(rules)
        y = np.arange(len(rules))[::-1]
        for yi, (rule, row) in zip(y, d.iterrows()):
            key = [k for k, v in RULES.items() if v == rule][0]
            ax.plot([row.recall_random_dates, row.recall], [yi, yi], color=GRID, linewidth=2, zorder=1)
            ax.scatter(row.recall_random_dates, yi, s=60, facecolors="white", edgecolors=MUTED, linewidths=1.5, zorder=2)
            ax.scatter(row.recall, yi, s=70, color=COLOR[key], zorder=3)
            ax.text(row.recall + 0.03, yi, f"{int(row.caught)}/{int(row.episodes)}", va="center", fontsize=8, color=INK)
        ax.set_yticks(y, rules); ax.set_xlim(0, 1.12); ax.set_title(per, fontsize=10, color=INK, loc="left")
        ax.set_xlabel("share of sustained rises caught", color="#52514e"); _style(ax); ax.grid(axis="x", color=GRID, linewidth=0.6)
    axes[0].scatter([], [], s=60, facecolors="white", edgecolors=MUTED, label="same alerts on random dates")
    axes[0].scatter([], [], s=70, color=INK, label="rule (colour per rule)")
    fig.legend(loc="lower center", ncol=2, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(path, dpi=200, facecolor="white"); plt.close(fig)


def fig_prices_alerts(D, alerts, eps, items, start, end, path):
    """Contains prices: written to the data folder only, never to git."""
    import matplotlib.pyplot as plt
    import matplotlib.transforms as mt
    fig, axes = plt.subplots(len(items), 1, figsize=(9, 2.4 * len(items)), sharex=True)
    for ax, it in zip(np.atleast_1d(axes), items):
        d = D[(D.item_id == it) & (D.Date >= start) & (D.Date <= end)]
        for _, e in eps[(eps.item_id == it) & (pd.to_datetime(eps.end_date) >= start) & (pd.to_datetime(eps.onset_date) <= end)].iterrows():
            ax.axvspan(pd.to_datetime(e.onset_date), pd.to_datetime(e.end_date), color=BAND, linewidth=0)
        ax.plot(d.Date, d.Price_Avg, color=INK, linewidth=1.1)
        tr = mt.blended_transform_factory(ax.transData, ax.transAxes)
        for yy, rule in ((1.04, "A"), (1.10, "B")):
            a = alerts[(alerts.item_id == it) & (alerts.rule == rule)].sort_values("target_idx")
            st = a[a.alert & ~a.alert.shift(1, fill_value=False)]
            st = st[(st.tdate >= start) & (st.tdate <= end)]
            ax.scatter(st.tdate, [yy] * len(st), marker="v", s=22, color=COLOR[rule], transform=tr, clip_on=False)
            ax.text(1.005, yy, RULES[rule], transform=ax.transAxes, fontsize=7, va="center", color="#52514e")
        ax.set_title(short(it) + f" (Tk {unit(it)})", fontsize=9, color=INK, loc="left", pad=22)
        _style(ax)
    fig.text(0.01, 0.005, "Shaded: sustained 10 % rise episodes. Triangles: start of an alert run.", fontsize=7, color="#52514e")
    fig.tight_layout(rect=(0, 0.02, 0.93, 1)); fig.savefig(path, dpi=200, facecolor="white"); plt.close(fig)


# ---------- register ----------
def register(T, commit, choice, choice_commit, audit, code_commit):
    D1, B5, M2, M3 = T["D1_panel_summary"], T["B5_rise_episodes_by_item_year"], T["M2_validation_models"], T["M3_test_accuracy"]
    A2, A3, A4 = T["A2_rule_comparison"].assign(p=lambda d: d.period.map(_period)), T["A3_rule_overlap"], T["A4_range_coverage"]
    rows = []
    def add(claim, value, table, retro=False):
        rows.append((claim, value, table, notebook_of(table), commit.get(table, ""), "retrospective" if retro else ""))
    add("Items and report days", f"{len(D1)} items x {int(D1.report_days.iloc[0]):,} report days, {D1.first_date.iloc[0]} to {D1.last_date.iloc[0]}", "D1_panel_summary")
    add("Price unchanged from the previous report day", f"{100 * D1.share_unchanged.min():.0f}-{100 * D1.share_unchanged.max():.0f} % of report days", "D1_panel_summary")
    e = B5.groupby("year").episodes_10pct.sum()
    add("Sustained 10 % rise episodes (onset year)", f"{int(e.sum())} in 2021-26; {int(e.get(2024, 0))} in 2024; {int(e.get(2025, 0) + e.get(2026, 0))} in 2025-26", "B5_rise_episodes_by_item_year")
    none = B5[B5.year >= 2024].groupby("item_id").episodes_10pct.sum()
    add("Items with no sustained rise in 2024-26", ", ".join(short(i) for i in none[none == 0].index), "B5_rise_episodes_by_item_year")
    for M, nm, retro in ((M2, "M2_validation_models", False), (M3, "M3_test_accuracy", True)):
        m = M[M.model != "naive"]
        per = "2025-26" if retro else "2024"
        add(f"Forecast relative MAE vs tomorrow = today, {per}", f"{m.gmean_rel_mae.min():.2f}-{m.gmean_rel_mae.max():.2f} (LightGBM and ETS, all horizons; none below 1)" if (m.gmean_rel_mae >= 1).all()
            else f"{m.gmean_rel_mae.min():.2f}-{m.gmean_rel_mae.max():.2f}", nm, retro)
        sig = m[m.p_holm < 0.05]
        add(f"Significant differences (DM, Holm 5 %), {per}", f"{len(sig)} of {len(m)}; {int((sig.gmean_rel_mae > 1).sum())} favour tomorrow = today", nm, retro)
    add("Alert settings fixed on 2024", f"ML range {choice['A']['setting']}, simple range {choice['B']['setting']}, fixed rise {choice['C']['setting']:.0%} (committed {choice_commit})", "A1_alert_choice")
    for _, x in A2.iterrows():
        add(f"{RULES[x.rule]}: rises caught, {x.p}", f"{int(x.detected)}/{int(x.episodes)} = {x.recall:.0%}; random dates {x.placebo_recall:.0%} (p = {x.placebo_p:.3f}); "
            f"{int(x.alert_runs)} alert runs; median delay {x.median_delay_reports:g} report days", "A2_rule_comparison", x.p == RETRO)
    for _, x in A3.iterrows():
        add(f"ML range vs simple range, {_period(x.period)}", f"both {x.both}, ML only {x.A_only}, simple only {x.B_only}, neither {x.neither} of {x.episodes}", "A3_rule_overlap", _period(x.period) == RETRO)
    add("Range coverage (nominal 95 %)", f"{A4.coverage.min():.3f}-{A4.coverage.max():.3f}; Kupiec p < 0.05 in " +
        ", ".join(sorted({_period(p) for p in A4[A4.kupiec_p < 0.05].period})) if (A4.kupiec_p < 0.05).any() else f"{A4.coverage.min():.3f}-{A4.coverage.max():.3f}", "A4_range_coverage", True)
    if audit is not None:
        a = dict(zip(audit.measure, audit.value))
        rows.append(("Data audit (earlier pipeline, not recomputed)", f"{a.get('price cells checked (Min and Max)')} price cells, {a.get('rows with a mismatch')} mismatches",
                     "archive/old_pipeline/reports/project/tables/P2_audit_summary.csv", "earlier pipeline", "", ""))
    reg = pd.DataFrame(rows, columns=["claim", "value", "source_table", "notebook", "table_commit", "label"])

    # Plan section 7 claims, checked against the results
    A = A2.set_index(["rule", "p"]).recall
    AB = A2[A2.rule.isin(["A", "B"])]          # the plan claims are about the two ranges; rule C is a reference point
    ratio, ab = AB.recall / AB.placebo_recall, AB.recall
    m3 = M3[M3.model != "naive"]
    plan = [
        ("Ranges hold about 94 % of prices against a 95 % target", f"coverage {A4.coverage.min():.3f}-{A4.coverage.max():.3f}",
         "supported" if A4.coverage.between(0.92, 0.96).all() else "not supported"),
        ("Alerts catch 65 to 75 % of sustained 10 % rises", f"ML and simple range {ab.min():.0%}-{ab.max():.0%}",
         "supported" if ab.between(0.65, 0.75).all() else "partly supported: " + ", ".join(f"{RULES[r]} {p} {v:.0%}" for (r, p), v in A.items() if r in "AB" and not 0.65 <= v <= 0.75) + " outside the range"),
        ("About three times what random dates catch", f"ML and simple range {ratio.min():.1f}-{ratio.max():.1f} times",
         "supported" if ratio.min() >= 2.8 else f"roughly: {ratio.min():.1f}-{ratio.max():.1f} times, a little under three"),
        ("Six forecast models compared; none beat tomorrow = today", "three models (naive, ETS, LightGBM); " + ("none beats it" if (m3.gmean_rel_mae >= 1).all() else "one beats it"),
         "changed: three models (DEVIATIONS 2026-11-17)"),
        ("Alerts start about 2 report days after onset", f"ML and simple range: median delay {AB.median_delay_reports.min():g}-{AB.median_delay_reports.max():g} report days",
         "supported" if AB.median_delay_reports.between(1, 3).all() else "not supported"),
    ]
    planT = pd.DataFrame(plan, columns=["plan claim", "result", "verdict"])
    md = ["# Results register", "",
          f"Generated by notebook 06_report_tables (code {code_commit}). Every number below comes from a committed table; the commit is the last one that changed that table. "
          "2025-26 results are **retrospective** (that period was already looked at by the earlier run). Alerts are abnormal-rise detection, not early warning.", "",
          "## Headline numbers", "", _md(reg), "", "## Claims from the project plan (section 7), checked", "", _md(planT), ""]
    return reg, planT, "\n".join(md)


def _md(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in cols) + " |")
    return "\n".join(lines)
