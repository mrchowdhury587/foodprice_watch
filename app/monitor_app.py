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

BANNER = "Replay of TCB Dhaka daily retail prices to 24 Oct 2026. Abnormal-rise detection, not early warning."

RULES_TABLE = pd.DataFrame({
    "Rule": ["ML range (LightGBM)", "Simple range (tomorrow = today)", "Fixed 7-report rise"],
    "Upper bound": ["forecast + 95th pct of last 120 errors", "no change + 95th pct of last 120 changes", "price 7 reports ago + 7 %"],
    "Alert": ["above on 3 of last 5 report days"] * 3,
})

TEXTS = [BANNER]


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
        return (f"Items in alert: **{n} of {len(T)}** · above the range: {above}", T)

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
        msg = f"{len(L)} alert runs"
        if len(sc):
            msg += f" · {int((sc.iloc[:, -1] == 'yes').sum())} of {len(sc)} scored runs matched a sustained rise"
        return msg, L

    r5 = R5.rename(columns={"recall": "share caught", "recall_random_dates": "random dates", "p": "p (random dates)"})
    with gr.Blocks(title="Food Price Watch", theme=gr.themes.Soft()) as app:
        gr.Markdown("# Food Price Watch\n" + BANNER)
        with gr.Tab("Status on a day"):
            with gr.Row():
                d_in = gr.Dropdown(days, value=days[0], label="Report day")
                r_in = gr.Radio(rule_names, value=mo.RULES[settings["monitor"]["main_rule"]], label="Alert rule")
            s_md = gr.Markdown()
            s_df = gr.Dataframe(interactive=False, wrap=True)
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
            gr.Dataframe(RULES_TABLE, interactive=False, wrap=True, label="Rules (settings chosen on 2024)")
            gr.Dataframe(r5, interactive=False, wrap=True, label="Scores against sustained 10 % rises")
            gr.Dataframe(R5b, interactive=False, label="Rises caught: ML range vs simple range")
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
