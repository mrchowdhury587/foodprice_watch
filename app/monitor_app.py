"""Food Price Watch monitor (Gradio). A replay of TCB Dhaka daily retail prices to 24 Oct 2026 with the three abnormal-rise rules.

On the work PC:
    set FW_DATA_ROOT=E:\\msc_project\\FoodPriceWatch_v2_local
    python app/monitor_app.py
In Colab: notebook 07_monitor (builds processed/monitor_8.csv, then launches this app).
The data holds TCB prices: a share link shows them to anyone who has it (approved by the user, DEVIATIONS.md)."""
import sys
from pathlib import Path

import gradio as gr
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from foodwatch import monitor as mo  # noqa: E402

BANNER = ("**Food Price Watch: monitoring and abnormal-rise alerts for daily retail food prices in Dhaka.** "
          "A replay of TCB's daily Dhaka price sheets to 24 October 2026 (no new prices are fetched). "
          "Each day's status uses only what was known that day. Alerts flag a price that stays above its expected range: "
          "abnormal-rise detection, not early warning. A rise above the range is a rise not explained by recent price behaviour or measured cost drivers.")

RULES_TEXT = """
### The three alert rules
Every report day the price is compared with the price expected 7 report days earlier.

- **ML range (LightGBM), the main rule here.** A LightGBM model forecasts the 7-report price change; the upper bound is the forecast plus the 95th percentile of the item's last 120 forecast errors.
- **Simple range (tomorrow = today).** The same, with "no change" as the forecast: the bound is the 95th percentile of the item's last 120 seven-report changes.
- **Fixed 7-report rise.** The price is at least 7 % above its level 7 report days earlier (the same for every item). It is close to the definition of a sustained rise, so its score is partly circular: a reference point, not the winner.

An **alert** is raised when the price was above the bound on at least 3 of the last 5 report days. An **alert run** starts on its first day.
All settings (95 %, 95 %, 7 %) were chosen on 2024 only and committed (commit e0cfa06) before 2025-26 was scored.

### How well they work
A **sustained rise** is a rise of at least 10 % over 14 report days that lasts at least 5 report days. An alert run counts for a rise if it starts from 14 report days before its onset to 7 after its end.
"Random dates" is the share of rises caught when each item's alert runs are moved to random dates (300 draws).
"""

FINDING = ("**Finding:** the simple range catches about as many sustained rises as the ML range (8 vs 6 of 11 in 2024; 15 vs 17 of 23 in 2025-26), "
           "and the two catch mostly the same rises. The alerts do not need the ML model. No forecast model beat \"tomorrow = today\".")

LIMITS = """
### Limits
- 2025-26 was already looked at by an earlier run of this project, so its results are **retrospective**.
- Soybean oil, palm oil and sugar had no sustained rise in 2024-26, so their alerts cannot be judged.
- The ranges hold 93-95 % of prices against a 95 % target; in 2025-26 slightly but significantly fewer.
- About 6 in 10 alert runs do not match a sustained rise (precision 0.35-0.41 for the two ranges).
- Alerts start a median of 1.5-2 report days after a rise begins.
"""

TEXTS = [BANNER, RULES_TEXT, FINDING, LIMITS]


def make_app(M, EP, settings, R5, R5b):
    days = mo.report_days(M)[::-1]
    items = [mo.short(i) for i in sorted(M.item_id.unique())]
    rule_names = list(mo.RULES.values())
    LOG = mo.alert_log(M, EP, settings, list("ABC"))

    def status(day, rule_name):
        r = mo.RULE_KEY[rule_name]
        T = mo.status_on(M, day, r)
        n = int((T.Status == "ALERT: abnormal rise").sum())
        above = int(T.Status.str.startswith("above").sum())
        return (f"**{day}**, rule: **{rule_name}**. Items in alert: **{n} of {len(T)}**; above the range but not (yet) in alert: {above}.", T)

    def item_view(item, rules, start, end):
        keys = [mo.RULE_KEY[x] for x in rules] or ["A"]
        if start > end:
            start, end = end, start
        fig = mo.item_chart(M, EP, item, keys, start, end)
        L = LOG[(LOG.item == item) & LOG.rule.isin([mo.RULES[k] for k in keys]) & LOG.start.between(start, end)]
        return fig, L

    def log_view(rules, item, period):
        L = LOG[LOG.rule.isin(rules)]
        if item != "all":
            L = L[L.item == item]
        if period != "all":
            L = L[L.period == period]
        sc = L[L.period != ""]
        msg = f"{len(L)} alert runs."
        if len(sc):
            msg += f" Of the {len(sc)} scored runs, {int((sc.iloc[:, -1] == 'yes').sum())} matched a sustained rise (hindsight)."
        return msg, L

    r5 = R5.rename(columns={"recall": "share caught", "recall_random_dates": "random dates", "p": "p (random dates)"})
    with gr.Blocks(title="Food Price Watch", theme=gr.themes.Soft()) as app:
        gr.Markdown("# Food Price Watch")
        gr.Markdown(BANNER)
        with gr.Tab("Status on a day"):
            with gr.Row():
                d_in = gr.Dropdown(days, value=days[0], label="Report day")
                r_in = gr.Radio(rule_names, value=mo.RULES[settings["monitor"]["main_rule"]], label="Alert rule")
            s_md = gr.Markdown()
            s_df = gr.Dataframe(interactive=False, wrap=True)
            gr.Markdown(FINDING)
            for c in (d_in, r_in):
                c.change(status, [d_in, r_in], [s_md, s_df])
            app.load(status, [d_in, r_in], [s_md, s_df])
        with gr.Tab("Item"):
            with gr.Row():
                i_in = gr.Dropdown(items, value="Onion - Local", label="Item")
                ir_in = gr.CheckboxGroup(rule_names, value=[mo.RULES[settings["monitor"]["main_rule"]]], label="Rules to show")
            with gr.Row():
                a_in = gr.Dropdown(days[::-1], value="2024-01-02" if "2024-01-02" in days else days[-1], label="From")
                b_in = gr.Dropdown(days, value=days[0], label="To")
            i_plot = gr.Plot()
            i_df = gr.Dataframe(interactive=False, wrap=True, label="Alert runs in this period")
            for c in (i_in, ir_in, a_in, b_in):
                c.change(item_view, [i_in, ir_in, a_in, b_in], [i_plot, i_df])
            app.load(item_view, [i_in, ir_in, a_in, b_in], [i_plot, i_df])
        with gr.Tab("Alert log"):
            with gr.Row():
                lr_in = gr.CheckboxGroup(rule_names, value=[mo.RULES[settings["monitor"]["main_rule"]]], label="Rules")
                li_in = gr.Dropdown(["all"] + items, value="all", label="Item")
                lp_in = gr.Radio(["all"] + list(mo.PERIODS), value="all", label="Period")
            l_md = gr.Markdown()
            l_df = gr.Dataframe(interactive=False, wrap=True)
            for c in (lr_in, li_in, lp_in):
                c.change(log_view, [lr_in, li_in, lp_in], [l_md, l_df])
            app.load(log_view, [lr_in, li_in, lp_in], [l_md, l_df])
        with gr.Tab("How it works"):
            gr.Markdown(RULES_TEXT)
            gr.Dataframe(r5, interactive=False, wrap=True, label="Rules scored against sustained 10 % rises (2025-26 retrospective)")
            gr.Dataframe(R5b, interactive=False, label="Rises caught by the ML range and the simple range")
            gr.Markdown(FINDING)
            gr.Markdown(LIMITS)
    return app


def load(data_root, repo):
    import yaml
    settings = yaml.safe_load((repo / "config/settings.yaml").read_text(encoding="utf-8"))
    M = pd.read_csv(data_root / settings["files"]["monitor"], parse_dates=["date"])
    for c in [c for c in M.columns if c.startswith(("exceed_", "alert_", "run_start_")) or c == "in_rise"]:
        M[c] = M[c].astype(str).str.lower().eq("true")
    EP = pd.read_csv(data_root / settings["files"]["rise_episodes"])
    T = repo / "reports/tables/report"
    return M, EP, settings, pd.read_csv(T / "R5_alert_rules.csv"), pd.read_csv(T / "R5b_rule_overlap.csv")


if __name__ == "__main__":
    from foodwatch.paths import DATA_ROOT, REPO
    make_app(*load(DATA_ROOT, REPO)).launch(share=False)
