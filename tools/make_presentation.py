"""Build the Food Price Watch presentation (.pptx) from the numbers in report v5.

Plain style: white slides, dark titles, native tables, speaker notes.
Every number below is copied from reports/thesis/report_v5 (chapters and tables); nothing is computed here.

Figures F1, F3, F4 come from reports/figures (in git). F2 and F5 show TCB prices, so they are read from
the local data folder and the output .pptx is written there too (never into git).

Usage:
    python tools/make_presentation.py [--short] [--data-root E:/msc_project/FoodPriceWatch_v2_local]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "thesis" / "report_v5"

DARK = RGBColor(0x1F, 0x2A, 0x44)   # titles
TEXT = RGBColor(0x26, 0x26, 0x26)   # body
MUTED = RGBColor(0x6B, 0x6B, 0x6B)  # captions
LIGHT = RGBColor(0xEE, 0xF1, 0xF6)  # table header / boxes
LINE = RGBColor(0xA6, 0xAE, 0xBF)
FONT = "Calibri"

W, H = 13.333, 7.5
NAIVE = "\u201ctomorrow = today\u201d"


# ----------------------------------------------------------------------------- helpers
def _font(run, size, bold=False, color=TEXT, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def text_box(slide, x, y, w, h, lines, size=18, bold=False, color=TEXT, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, italic=False):
    """lines: str or list of str; a line may be (text, {'bold':..,'size':..,'color':..})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    if isinstance(lines, str):
        lines = [lines]
    for i, line in enumerate(lines):
        opts = {}
        if isinstance(line, tuple):
            line, opts = line
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(opts.get("after", 4))
        r = p.add_run()
        r.text = line
        _font(r, opts.get("size", size), opts.get("bold", bold), opts.get("color", color),
              opts.get("italic", italic))
    return tb


def bullets(slide, x, y, w, h, items, size=18):
    """items: list of str or (str, level)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        level = 0
        if isinstance(it, tuple):
            it, level = it
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8 if level == 0 else 4)
        marker = "\u2022  " if level == 0 else "\u2013  "
        indent = "      " * level
        # A label before ':' is bold.
        if level == 0 and ": " in it and it.index(": ") < 40:
            head, tail = it.split(": ", 1)
            r = p.add_run(); r.text = indent + marker + head + ": "; _font(r, size, True)
            r = p.add_run(); r.text = tail; _font(r, size)
        else:
            r = p.add_run(); r.text = indent + marker + it
            _font(r, size - 2 if level else size, color=TEXT if level == 0 else MUTED)
    return tb


def table(slide, x, y, w, rows, col_w=None, size=14, row_h=0.4, first_col_bold=False, highlight=(), left_cols=(0,)):
    nr, nc = len(rows), len(rows[0])
    shape = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tbl = shape.table
    tbl.first_row = True
    if col_w:
        total = sum(col_w)
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = Inches(w * cw / total)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = DARK
            elif i in highlight:
                cell.fill.fore_color.rgb = RGBColor(0xFF, 0xF4, 0xD6)
            else:
                cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else LIGHT
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j in left_cols else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = str(val)
            _font(r, size, bold=(i == 0) or (first_col_bold and j == 0),
                  color=RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else TEXT)
    return shape


def picture(slide, path, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    if not Path(path).exists():
        return text_box(slide, x, y, w or 4, 1, f"[missing figure: {Path(path).name}]", 14, color=MUTED)
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def box(slide, x, y, w, h, text, size=14, fill=LIGHT, bold=False, dashed=False):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.12
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.color.rgb = LINE
    s.line.width = Pt(1.25)
    if dashed:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        s.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    s.shadow.inherit = False
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = line
        _font(r, size, bold=bold or i == 0 and "\n" in text)
    return s


def arrow(slide, x1, y1, x2, y2, dashed=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = DARK
    c.line.width = Pt(2)
    if dashed:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd",
                          {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


class Deck:
    """keep: 1-based positions (in the full deck) of the slides to keep; None keeps all.
    A skipped slide is drawn into a scratch presentation that is never saved."""

    def __init__(self, keep=None):
        self.prs, self.scratch = Presentation(), Presentation()
        for p in (self.prs, self.scratch):
            p.slide_width = Inches(W)
            p.slide_height = Inches(H)
        self.keep = keep
        self.i = 0  # position in the full deck
        self.n = 0  # number shown on the slide

    def slide(self, title=None, notes=""):
        self.i += 1
        if self.keep is not None and self.i not in self.keep:
            return self.scratch.slides.add_slide(self.scratch.slide_layouts[6])
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.n += 1
        if title:
            text_box(s, 0.6, 0.35, W - 1.2, 0.9, title, 32, bold=True, color=DARK,
                     anchor=MSO_ANCHOR.MIDDLE)
        if self.n > 1:
            text_box(s, W - 1.4, H - 0.5, 0.9, 0.35, str(self.n), 11, color=MUTED, align=PP_ALIGN.RIGHT)
            text_box(s, 0.6, H - 0.5, 6, 0.35, "Food Price Watch", 11, color=MUTED)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s


# ----------------------------------------------------------------------------- slides
# Short version: title, background, RQs, data, alert method, results, app, conclusion, limits, thanks.
SHORT = {1, 3, 5, 7, 11, 13, 15, 16, 17, 18, 19, 20, 21}


def build(data_root: Path, out: Path, keep=None):
    figs = REPO / "reports" / "figures"
    local_figs = data_root / "reports" / "figures"
    d = Deck(keep)

    # 1 Title
    s = d.slide(notes="Introduce the project: a daily monitor that tells, for eight everyday food items in "
                      "Dhaka, whether today's price is unusually high, and an honest test of whether "
                      "machine learning makes that monitor better.")
    picture(s, REPORT / "unilogo.png", W / 2 - 0.65, 0.45, w=1.3)
    text_box(s, 0.8, 1.9, W - 1.6, 1.4,
             ["Food Price Watch",
              ("A Monitoring and Abnormal-Rise Alert System for Daily Retail Food Prices in Dhaka",
               {"size": 24, "bold": False, "color": TEXT})],
             40, bold=True, color=DARK, align=PP_ALIGN.CENTER)
    text_box(s, 0.8, 3.75, W - 1.6, 2.9,
             [("Md. Romjan Chowdhury  |  ID: 22408024", {"bold": True, "size": 20}),
              ("Research Project, Master of Science (Engineering)", {"size": 18}),
              ("Department of Computer Science and Engineering, Comilla University", {"size": 18}),
              ("Supervisor: Dr. Mahmudul Hasan, Associate Professor", {"size": 18, "after": 10}),
              ("November 2026", {"size": 16, "color": MUTED})],
             18, align=PP_ALIGN.CENTER)

    # 2 Outline
    s = d.slide("Outline", "The talk follows the report: the problem, the data, the two methods (forecast "
                           "benchmark and alert rules), the results for each research question, the app, "
                           "and the conclusion.")
    items = ["Background and problem", "Research questions", "Related work and research gap", "Data",
             "Method: forecast benchmark", "Method: alert system", "System architecture",
             "Results: price behaviour (RQ1)", "Results: forecasts (RQ2)", "Results: alerts (RQ3, RQ4)",
             "Monitoring app and a worked example", "Conclusion, limitations, future work"]
    for i, it in enumerate(items):
        col, row = divmod(i, 6)
        x, y = 0.9 + col * 6.0, 1.55 + row * 0.82
        box(s, x, y, 0.55, 0.55, str(i + 1), 16, fill=DARK, bold=True).text_frame.paragraphs[0].runs[0] \
            .font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        text_box(s, x + 0.75, y, 5.0, 0.55, it, 20, anchor=MSO_ANCHOR.MIDDLE)

    # 3 Background
    s = d.slide("Background and motivation",
                "Food is a large part of household spending, and prices in Dhaka can jump within weeks. "
                "TCB publishes daily prices, but one sheet per day does not tell you whether today's price "
                "is unusual. FAO and WFP have anomaly indicators, but for monthly data.")
    bullets(s, 0.6, 1.45, 7.6, 5.2, [
        "Food prices in Dhaka can rise sharply within weeks (onion, potato, eggs, broiler chicken)",
        "Food is 59 % of the consumer price index basket; food inflation has reached about 14 % at its peaks",
        "TCB publishes a daily sheet of Dhaka retail prices (lowest and highest price per item)",
        "One document per day: it does not show whether today's price is unusual, or whether a rise is continuing",
        "FAO and WFP watch prices for anomalies, but their indicators are built for monthly market prices",
    ], 18)
    for i, (big, small) in enumerate([("8", "everyday food items"), ("1,412", "TCB report days"),
                                      ("2021-26", "17 May 2021 to 24 Oct 2026")]):
        y = 1.55 + i * 1.65
        box(s, 8.8, y, 3.9, 1.4, "", fill=LIGHT)
        text_box(s, 8.8, y + 0.1, 3.9, 0.8, big, 36, bold=True, color=DARK, align=PP_ALIGN.CENTER)
        text_box(s, 8.8, y + 0.85, 3.9, 0.45, small, 15, color=MUTED, align=PP_ALIGN.CENTER)

    # 4 Problem and objectives
    s = d.slide("Problem statement and objectives",
                "The system must give each item an expected price range every report day and alert when the "
                "price stays above it. The evaluation has to be honest: settings chosen on one period and "
                "scored on another, and every forecast compared with the no-change forecast.")
    text_box(s, 0.6, 1.4, W - 1.2, 1.2,
             "Build and evaluate a system that gives each item an expected price range for each report day and "
             "raises an alert when the price stays above it, evaluated honestly: settings chosen on one period "
             f"and scored on another, every forecast compared with {NAIVE}, alerts compared with random dates.",
             18, italic=True)
    bullets(s, 0.6, 2.85, W - 1.2, 4.0, [
        "O1: A clean, audited daily table of TCB prices for 8 items, with weather, exchange rate and calendar joined on their availability date",
        "O2: Describe how the prices behave and define sustained rises from the prices alone",
        f"O3: Benchmark ETS and LightGBM forecasts against {NAIVE} at 1 to 30 report days",
        "O4: Build three alert rules, choose their settings on 2024, score them on 2025-26",
        "O5: A working monitoring app that shows which items are in alert on any report day",
    ], 17)

    # 5 Research questions
    s = d.slide("Research questions",
                "Four questions. RQ1 is descriptive. RQ2 is the forecast benchmark. RQ3 and RQ4 are about the "
                "alerts: do they beat chance, and does machine learning help?")
    table(s, 0.6, 1.5, W - 1.2, [
        ["RQ", "Question"],
        ["RQ1", "How do TCB daily retail prices for the eight items behave: how often and by how much do "
                "they change, and how often do sustained rises occur?"],
        ["RQ2", f"Does a machine-learning or statistical forecast beat {NAIVE} on these prices?"],
        ["RQ3", "Do alerts built from an expected price range catch sustained rises more often than the "
                "same number of alerts on random dates?"],
        ["RQ4", f"Does a range drawn from a machine-learning forecast catch more rises than a range drawn "
                f"from {NAIVE} or a fixed threshold?"],
    ], col_w=[1, 11], size=17, row_h=0.95, first_col_bold=True, left_cols=(0, 1))

    # 6 Related work
    s = d.slide("Related work and research gap",
                "Existing indicators are monthly. Many machine-learning studies of food prices never compare "
                "with the no-change forecast. And forecast-based alerts are rarely compared with alerts that "
                "need no model, or tested against chance.")
    text_box(s, 0.6, 1.4, 6.0, 0.5, "Related work", 22, bold=True, color=DARK)
    bullets(s, 0.6, 2.0, 6.0, 4.8, [
        "Monitoring indicators: FAO price anomaly indicator (growth rates vs history); WFP Alert for Price Spikes (price vs seasonal trend), both monthly",
        "Retail prices are sticky: they change rarely, in steps",
        "Forecasting: many ML studies compare models with each other or with ARIMA, not with no change",
        "Random walk is hard to beat out of sample",
        "Ranges from past out-of-sample forecast errors (Lee and Scholtes)",
    ], 16)
    text_box(s, 7.0, 1.4, 5.7, 0.5, "Research gap", 22, bold=True, color=DARK)
    for i, g in enumerate(["No tested daily monitor for Dhaka retail prices",
                           "ML food-price studies often report no no-change benchmark",
                           "Forecast-based alerts are rarely compared with model-free alerts or with chance"]):
        y = 2.0 + i * 1.5
        box(s, 7.0, y, 0.6, 0.6, str(i + 1), 18, fill=DARK, bold=True).text_frame.paragraphs[0].runs[0] \
            .font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        text_box(s, 7.8, y - 0.3, 4.9, 1.2, g, 17, anchor=MSO_ANCHOR.MIDDLE)

    # 7 Data
    s = d.slide("Data: TCB daily retail prices, 8 items",
                "Prices are the midpoint of TCB's lowest and highest Dhaka price. 11,296 item-days. Missing "
                "prices are rare. An audit of the converted sheets compared 3,060 price cells with the "
                "originals and found no mismatch. Drivers are used only for some items.")
    table(s, 0.6, 1.4, 8.0, [
        ["Item", "Unit", "Group", "Drivers", "Not rep. %"],
        ["Chicken - Broiler", "per kg", "volatile perishable", "none", "0.00"],
        ["Egg - Farm", "per hali (4)", "volatile perishable", "none", "0.07"],
        ["Onion - Local", "per kg", "volatile perishable", "weather", "0.07"],
        ["Potato", "per kg", "domestic staple", "weather", "0.07"],
        ["Garlic - Imported", "per kg", "imported staple", "exchange rate", "0.07"],
        ["Palm Oil - Loose", "per litre", "administered", "exchange rate", "0.00"],
        ["Soybean Oil - Loose", "per litre", "administered", "exchange rate", "0.28"],
        ["Sugar", "per kg", "administered", "exchange rate", "0.00"],
    ], col_w=[2.3, 1.5, 2.2, 1.7, 1.2], size=14, row_h=0.5)
    bullets(s, 9.0, 1.4, 3.8, 5.3, [
        "Source: TCB daily sheets, Dhaka",
        "Period: 17 May 2021 to 24 Oct 2026",
        "Size: 11,296 item-days on 1,412 report days",
        "Audit: 3,060 price cells re-read, no mismatch",
        "Other files: Ramadan/Eid dates, Tk/USD rate, Open-Meteo weather (13 locations)",
    ], 16)

    # 8 Cleaning rules
    s = d.slide("Cleaning rules and availability dates",
                "These rules stop the model from seeing anything it could not have known on the day. Missing "
                "prices are never imputed in a target. The sparse 2022 period is kept as a gap and never "
                "scored. Drivers join on the date they became available.")
    rules = [("Missing price", "A blank or zero price is \u201cnot reported\u201d; never imputed in a target"),
             ("2022 gap", "12 Mar to 31 Dec 2022 is sparse: never filled across, never scored"),
             ("Real jumps", "Kept; never removed as outliers"),
             ("Weather", "Usable 5 days after the day it describes"),
             ("Exchange rate", "Last value on or before the report date; older than 7 days left empty"),
             ("Raw files", "Copied once into raw/, never edited, listed with sha256 hashes")]
    for i, (k, v) in enumerate(rules):
        col, row = divmod(i, 3)
        x, y = 0.6 + col * 6.2, 1.5 + row * 1.7
        box(s, x, y, 5.9, 1.45, "", fill=LIGHT)
        text_box(s, x + 0.2, y + 0.1, 5.5, 0.45, k, 19, bold=True, color=DARK)
        text_box(s, x + 0.2, y + 0.55, 5.5, 0.85, v, 16)

    # 9 Splits
    s = d.slide("Training, validation and test",
                "Data is never shuffled. Every choice of model setting, alert level and threshold is made on "
                "2024 and committed before 2025-26 is scored. 2025-26 had been looked at in an earlier run of "
                "the project, so its results are labelled retrospective.")
    segs = [("History (training only)\nMay 2021 - 2023", 0.6, 4.6, LIGHT),
            ("Validation\n2024", 5.3, 3.0, RGBColor(0xD6, 0xE4, 0xF5)),
            ("Test (retrospective)\n2025 - Oct 2026", 8.4, 4.3, RGBColor(0xFF, 0xF4, 0xD6))]
    for t, x, w, f in segs:
        box(s, x, 1.5, w, 1.0, t, 16, fill=f)
    table(s, 0.6, 2.85, W - 1.2, [
        ["Period", "Report days", "Item-days", "Origins", "Forecasts", "Sustained rises"],
        ["History (May 2021 - 2023), training only", "480", "3,840", "--", "--", "36"],
        ["2024 validation", "329", "2,632", "43", "344", "11"],
        ["2025 - Oct 2026 test (retrospective)", "603", "4,824", "82", "656", "23"],
        ["All", "1,412", "11,296", "125", "1,000", "70"],
    ], col_w=[4.2, 1.5, 1.5, 1.3, 1.4, 1.8], size=15, row_h=0.48)
    bullets(s, 0.6, 5.45, W - 1.2, 1.4, [
        "Expanding window: a model fitted at a forecast origin sees only targets on or before that origin",
        "Origins every 7 report days; settings committed (commits 8d7c145, e0cfa06) before 2025-26 was scored",
    ], 16)

    # 10 Forecast benchmark
    s = d.slide("Method: forecast benchmark",
                "All models forecast the change in the log price over h report days, so items with different "
                "price levels are on the same scale. LightGBM settings were chosen on 2024 from 16 "
                "configurations; the simplest within 1 % of the best was taken.")
    for i, (name, desc) in enumerate([
            (f"Naive", f"{NAIVE}: forecast change is zero"),
            ("ETS", "AutoETS on each item's log price (statsforecast), refit every origin"),
            ("LightGBM", "One global model, all items and horizons; price-history inputs; 7 leaves, lr 0.03, L1 loss, 300 rounds")]):
        x = 0.6 + i * 4.1
        box(s, x, 1.45, 3.85, 1.45, "", fill=LIGHT)
        text_box(s, x + 0.15, 1.5, 3.55, 0.5, name, 20, bold=True, color=DARK)
        text_box(s, x + 0.15, 1.95, 3.55, 0.95, desc, 15)
    bullets(s, 0.6, 3.25, W - 1.2, 3.4, [
        "Target: y = log P(t+h) - log P(t), horizons h = 1, 7, 14, 30 report days",
        f"Relative MAE: model MAE / MAE of {NAIVE}, geometric mean over items; below 1 = better than {NAIVE}",
        "Significance: Diebold-Mariano test (Harvey-Leybourne-Newbold correction), Holm correction",
        "Accuracy (1 - MAPE) is shown only next to the naive accuracy: on sticky prices a high accuracy costs nothing",
    ], 17)

    # 11 Alert system
    s = d.slide("Method: the alert system",
                "The upper bound for a day is fixed one week earlier: forecast plus the 95th percentile of the "
                "item's last 120 known errors. One day above is not an alert; 3 of the last 5 is. The three "
                "rules differ only in how the bound is drawn.")
    steps = ["7-day forecast\nmade at t-7",
             "+ 95th pct of last\n120 known errors",
             "Upper bound\nfor day t",
             "Price above bound\non 3 of last 5 days",
             "Alert run\n(first day reported)"]
    for i, t in enumerate(steps):
        x = 0.6 + i * 2.5
        box(s, x, 1.5, 2.1, 1.15, t, 14)
        if i < len(steps) - 1:
            arrow(s, x + 2.1, 2.07, x + 2.5, 2.07)
    table(s, 0.6, 3.0, 7.4, [
        ["Rule", "Upper bound drawn from", "Chosen on 2024"],
        ["A. ML range", "LightGBM forecast + its past errors", "level 0.95"],
        ["B. Simple range", f"{NAIVE} + past 7-day price changes", "level 0.95"],
        ["C. Fixed rise", "Fixed % rise over 7 report days", "7 %"],
    ], col_w=[1.8, 3.8, 1.6], size=14, row_h=0.5)
    text_box(s, 8.4, 3.0, 4.4, 0.45, "Sustained rise (reference)", 19, bold=True, color=DARK)
    bullets(s, 8.4, 3.5, 4.4, 3.3, [
        "Rise ratio R = P(t) / P(t-14) - 1",
        "Rise day: R \u2265 10 %",
        "Episode: \u2265 5 consecutive rise days",
        "Defined from prices only, no model",
    ], 15)
    text_box(s, 0.6, 5.25, 7.4, 1.4,
             "Settings: most sensitive one with \u2264 2 unmatched alert runs per item-year (250 report days). "
             "Abnormal-rise detection, not early warning.", 15, italic=True, color=MUTED)

    # 12 Architecture
    s = d.slide("System architecture",
                "Four layers. Only rule A needs the LightGBM model; rule B uses no-change and rule C uses no "
                "forecast. The evaluation block is for this study only and is not needed to run the monitor.")
    layers = [("Data", "TCB sheets, weather,\nexchange rate, calendar \u2192 clean, join on availability date, check \u2192 one row per item-day"),
              ("Forecast", f"LightGBM (global model) and {NAIVE} \u2192 7-day forecasts every report day"),
              ("Alert engine", "Last 120 known errors \u2192 upper bound (rules A, B, C) \u2192 above on 3 of 5 \u21d2 alert run"),
              ("Presentation", "Gradio app: Status on a day | Item chart | Alert log | How it works")]
    for i, (name, desc) in enumerate(layers):
        y = 1.45 + i * 1.3
        box(s, 0.6, y, 2.2, 1.0, name, 17, fill=DARK, bold=True).text_frame.paragraphs[0].runs[0] \
            .font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        box(s, 3.0, y, 6.8, 1.0, desc.replace("\n", " "), 15)
        if i < 3:
            arrow(s, 6.4, y + 1.0, 6.4, y + 1.3)
    box(s, 10.3, 2.9, 2.4, 1.9, "Evaluation\n(study only)\nrises, random dates, coverage", 14, dashed=True)
    arrow(s, 9.8, 3.85, 10.3, 3.85, dashed=True)

    # 13 RQ1 behaviour
    s = d.slide("RQ1: prices rarely change",
                "An item's price is unchanged on 62 to 87 % of report days. Changes come in steps: median "
                "change sizes are 1 to 6 %. This stickiness is why forecasting these prices is hard.")
    picture(s, figs / "F1_change_frequency.png", 0.6, 1.4, w=6.6)
    table(s, 7.5, 1.4, 5.25, [
        ["Item", "Days changed %", "Median size %", "10 % rises"],
        ["Chicken", "37.5", "2.70", "8"],
        ["Egg", "22.9", "2.35", "8"],
        ["Garlic", "23.6", "4.00", "12"],
        ["Onion", "31.8", "5.00", "19"],
        ["Palm oil", "18.8", "1.02", "1"],
        ["Potato", "21.8", "6.25", "18"],
        ["Soybean oil", "19.4", "0.88", "1"],
        ["Sugar", "12.6", "1.85", "3"],
    ], col_w=[1.6, 1.4, 1.4, 1.1], size=13, row_h=0.45)
    text_box(s, 0.6, 5.2, 6.6, 1.5,
             ["Unchanged on 62-87 % of report days (2021-26)",
              ("70 sustained 10 % rises, mostly onion, potato and garlic", {"size": 17, "bold": False})],
             20, bold=True, color=DARK)

    # 14 RQ1 rises
    s = d.slide("RQ1: sustained rises",
                "Sustained rises are concentrated in onion, potato and imported garlic. Palm oil, soybean oil "
                "and sugar have no 10 % rise in 2024 or 2025-26, so recall cannot be measured for them. The "
                "7 and 15 % counts are a sensitivity check only.")
    picture(s, local_figs / "F2_prices_with_rises.png", 0.6, 1.3, h=5.25)
    table(s, 7.1, 1.4, 5.65, [
        ["Period", "7 %", "10 %", "15 %"],
        ["2021-26, all", "--", "70", "--"],
        ["2024 validation", "17", "11", "8"],
        ["2025-26 (retro.)", "26", "23", "15"],
    ], col_w=[2.4, 1, 1, 1], size=15, row_h=0.5)
    bullets(s, 7.1, 3.7, 5.65, 3.0, [
        "No 10 % rise in 2024 or 2025-26 for palm oil, soybean oil, sugar",
        "Before Ramadan: no consistent rise; chicken rises slightly more often, potato and onion less",
    ], 16)
    text_box(s, 0.6, 6.58, 6.3, 0.3, "Sustained rises shaded (notebook 06).", 11, color=MUTED)

    # 15 RQ2
    s = d.slide(f"RQ2: no model beats {NAIVE}",
                "Relative MAE is above 1 at every horizon in both periods, so both models are slightly worse "
                "than no-change. Every significant difference favours no-change. The drivers did not help "
                "either. This is the main negative result of the benchmark.")
    picture(s, figs / "F3_forecast_vs_naive.png", 0.6, 1.3, w=7.4)
    table(s, 8.3, 1.4, 4.45, [
        ["Rel. MAE", "2024", "2025-26"],
        ["ETS h=1", "1.060", "1.127"],
        ["ETS h=7", "1.010", "1.028"],
        ["ETS h=14", "1.004", "1.019"],
        ["ETS h=30", "1.002", "1.020"],
        ["LGBM h=1", "1.114", "1.213"],
        ["LGBM h=7", "1.029", "1.033"],
        ["LGBM h=14", "1.035", "1.014"],
        ["LGBM h=30", "1.014", "1.022"],
    ], col_w=[1.7, 1.3, 1.4], size=13, row_h=0.42)
    bullets(s, 0.6, 4.45, 7.4, 2.4, [
        "Relative MAE 1.00-1.11 in 2024 and 1.01-1.21 in 2025-26 (retrospective); 1 = equal to naive",
        f"Every significant difference (Holm-corrected DM test) favours {NAIVE}",
        "Why: on prices that are unchanged most days, the last price is the best guess",
    ], 16)

    # 16 RQ3/RQ4
    s = d.slide("RQ3: all three alert rules beat random dates",
                "Alerts are scored against sustained rises defined from prices alone. The two ranges reach "
                "about 2.5 to 2.8 times the recall of the same alerts placed on random dates; all three rules "
                "have p = 0.003, the smallest possible with 300 draws. Median delay 1.5 to 2 report days.")
    table(s, 0.6, 1.4, W - 1.2, [
        ["Period", "Rule", "Caught", "Recall", "Random", "p", "Runs", "Precision", "Delay"],
        ["2024 validation", "A. ML range", "6/11", "0.55", "0.20", "0.003", "17", "0.35", "1.5"],
        ["", "B. Simple range", "8/11", "0.73", "0.30", "0.003", "20", "0.40", "2"],
        ["", "C. Fixed 7 %", "10/11", "0.91", "0.49", "0.003", "27", "0.37", "0.5"],
        ["2025-26 (retro.)", "A. ML range", "17/23", "0.74", "0.28", "0.003", "42", "0.40", "2"],
        ["", "B. Simple range", "15/23", "0.65", "0.25", "0.003", "39", "0.38", "2"],
        ["", "C. Fixed 7 %", "22/23", "0.96", "0.31", "0.003", "30", "0.73", "2"],
    ], col_w=[2.2, 2.0, 1, 1, 1, 0.9, 0.8, 1.1, 0.8], size=14, row_h=0.42)
    picture(s, figs / "F4_alert_recall.png", 0.6, 4.55, h=2.3)
    bullets(s, 7.8, 4.55, 5.0, 2.3, [
        "Random: recall of the same alerts on random dates",
        "Delay: median report days from rise onset to alert",
        "Rule C is close to the rise definition, so its score is partly circular",
    ], 14)

    # 17 RQ4
    s = d.slide("RQ4: the ML range adds nothing over the simple range",
                "The ML range and the simple range catch nearly the same rises. In 2025-26 the ML range caught "
                "2 rises the simple range missed; in 2024 it was the other way round. So the monitor does not "
                "need machine learning. Coverage was slightly below 95 % in 2025-26.")
    text_box(s, 0.6, 1.4, 6.0, 0.45, "Which rises each range caught", 19, bold=True, color=DARK)
    table(s, 0.6, 1.9, 6.0, [
        ["Period", "Rises", "Both", "ML only", "Simple only", "Neither"],
        ["2024", "11", "6", "0", "2", "3"],
        ["2025-26 (retro.)", "23", "15", "2", "0", "6"],
    ], col_w=[2.0, 0.9, 0.8, 1.0, 1.2, 1.0], size=14, row_h=0.5)
    text_box(s, 7.0, 1.4, 5.7, 0.45, "Range coverage (nominal 0.95)", 19, bold=True, color=DARK)
    table(s, 7.0, 1.9, 5.75, [
        ["Period", "Rule", "Coverage", "Kupiec p"],
        ["2024", "A. ML", "0.945", "0.205"],
        ["2024", "B. Simple", "0.946", "0.358"],
        ["2025-26", "A. ML", "0.934", "<0.001"],
        ["2025-26", "B. Simple", "0.939", "0.001"],
    ], col_w=[1.4, 1.5, 1.4, 1.4], size=14, row_h=0.45)
    box(s, 0.6, 4.6, W - 1.2, 1.25,
        "Same rises, no model to train, easier to explain\n"
        "\u2192 for a daily monitor of these prices, a range drawn from each item's own past price changes is enough",
        18)

    # 18 App + worked example
    s = d.slide("Monitoring app and a worked example",
                "Worked example: local onion. The sustained rise began on 2 November 2025 and lasted 16 report "
                "days, with a peak rise of 57 % over 14 report days. Onion was above the ML bound on the onset "
                "day and the next; on 4 November, the third day above in five, the alert run started.")
    text_box(s, 0.6, 1.35, 5.9, 0.45, "Gradio app, four tabs", 19, bold=True, color=DARK)
    bullets(s, 0.6, 1.85, 5.9, 2.4, [
        "Status on a day: 8 items, price, bound, status",
        "Item: price, bounds and alerts on a chart",
        "Alert log: every alert run, filterable",
        "How it works: the three rules and scores",
    ], 15)
    text_box(s, 0.6, 4.05, 5.9, 0.45, "Onion, November 2025 (retrospective)", 19, bold=True, color=DARK)
    for i, (d_, t) in enumerate([("2 Nov", "Rise begins; above bound (day 1)"),
                                 ("3 Nov", "Above bound (day 2): no alert yet"),
                                 ("4 Nov", "3rd day above in last 5: alert run starts")]):
        y = 4.6 + i * 0.7
        box(s, 0.6, y, 1.2, 0.55, d_, 14, bold=True)
        text_box(s, 1.95, y, 4.6, 0.55, t, 15, anchor=MSO_ANCHOR.MIDDLE)
    picture(s, local_figs / "F5_prices_with_alerts.png", 6.9, 1.3, h=5.1)
    text_box(s, 6.9, 6.45, 5.9, 0.3, "Onion, potato, egg 2024-26: rises shaded, alert starts marked.",
             11, color=MUTED)

    # 19 Conclusion
    s = d.slide("Conclusion",
                "Summarise one answer per research question. The headline: the alerts work, the machine "
                "learning does not add anything, and the simple range is the practical choice.")
    for i, (rq, ans) in enumerate([
            ("RQ1", "Prices are sticky (unchanged 62-87 % of days), yet 70 sustained 10 % rises occur, mostly onion, potato, garlic"),
            ("RQ2", f"Neither ETS nor LightGBM beats {NAIVE} at any horizon (rel. MAE 1.00-1.21)"),
            ("RQ3", "All rules beat random dates (p = 0.003); ML range 17/23, simple range 15/23 in 2025-26, median 2 days after onset"),
            ("RQ4", "ML and simple ranges catch nearly the same rises: the monitor does not need machine learning")]):
        y = 1.4 + i * 1.22
        box(s, 0.6, y, 1.3, 1.0, rq, 20, fill=DARK, bold=True).text_frame.paragraphs[0].runs[0] \
            .font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        text_box(s, 2.15, y, 10.6, 1.0, ans, 18, anchor=MSO_ANCHOR.MIDDLE)
    text_box(s, 0.6, 6.35, W - 1.2, 0.4,
             "Alerts flag rises not explained by measured cost drivers; they are abnormal-rise detection, not early warning.",
             14, italic=True, color=MUTED)

    # 20 Limitations and future work
    s = d.slide("Limitations and future work",
                "Be open about the limits: the test period is retrospective, the items were chosen after an "
                "earlier run, and there are few rises. Future work is mainly running the monitor forward on "
                "new sheets.")
    text_box(s, 0.6, 1.4, 6.0, 0.45, "Limitations", 21, bold=True, color=DARK)
    bullets(s, 0.6, 1.95, 6.0, 4.9, [
        "2025-26 results are retrospective (seen in an earlier run)",
        "Eight items chosen after earlier results were seen",
        "Few sustained rises (11 in 2024, 23 in 2025-26); none for three items",
        "Rule C is partly circular",
        "Range slightly too narrow in 2025-26 (93.4-93.9 % vs 95 %)",
        "Rises only, Dhaka only, replays past data",
    ], 16)
    text_box(s, 7.0, 1.4, 5.7, 0.45, "Future work", 21, bold=True, color=DARK)
    bullets(s, 7.0, 1.95, 5.75, 4.9, [
        "Connect to new TCB sheets (with permission) and run forward on unseen days",
        "More items, falls as well as rises, other cities",
        "A range that adapts faster when an item becomes more volatile",
        "Compare with FAO and WFP indicators; test weekly or monthly drivers at longer horizons",
    ], 16)

    # 21 Thank you
    s = d.slide(notes="Invite questions.")
    text_box(s, 0.8, 2.5, W - 1.6, 1.2, "Thank you", 48, bold=True, color=DARK, align=PP_ALIGN.CENTER)
    text_box(s, 0.8, 3.8, W - 1.6, 0.8, "Questions?", 28, color=TEXT, align=PP_ALIGN.CENTER)

    out.parent.mkdir(parents=True, exist_ok=True)
    d.prs.save(out)
    print(f"saved {out} ({d.n} slides)")


# ----------------------------------------------------------------------------- simple version
def stat(slide, x, y, w, big, small, big_size=40):
    """A light card with a big number and a short label under it."""
    box(slide, x, y, w, 1.75, "", fill=LIGHT)
    text_box(slide, x, y + 0.12, w, 0.95, big, big_size, bold=True, color=DARK, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
    text_box(slide, x + 0.15, y + 1.05, w - 0.3, 0.65, small, 15, color=TEXT, align=PP_ALIGN.CENTER)


def white_label(shape):
    shape.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def build_simple(data_root: Path, out: Path):
    """Plain-language version for a general audience: few numbers, no statistical tests."""
    local_figs = data_root / "reports" / "figures"
    d = Deck()
    same = "\u201ctomorrow's price = today's price\u201d"

    # 1 Title
    s = d.slide(notes="This project checks Dhaka food prices every day and warns when a price rises in an "
                      "unusual way. It also tests whether machine learning makes those warnings better.")
    picture(s, REPORT / "unilogo.png", W / 2 - 0.65, 0.45, w=1.3)
    text_box(s, 0.8, 1.9, W - 1.6, 1.4,
             ["Food Price Watch",
              ("Spotting unusual rises in daily food prices in Dhaka", {"size": 24, "bold": False, "color": TEXT})],
             40, bold=True, color=DARK, align=PP_ALIGN.CENTER)
    text_box(s, 0.8, 3.75, W - 1.6, 2.9,
             [("Md. Romjan Chowdhury  |  ID: 22408024", {"bold": True, "size": 20}),
              ("Research Project, Master of Science (Engineering)", {"size": 18}),
              ("Department of Computer Science and Engineering, Comilla University", {"size": 18}),
              ("Supervisor: Dr. Mahmudul Hasan, Associate Professor", {"size": 18, "after": 10}),
              ("November 2026", {"size": 16, "color": MUTED})],
             18, align=PP_ALIGN.CENTER)

    # 2 Problem
    s = d.slide("The problem",
                "The government agency TCB writes down Dhaka market prices every working day. But a long list of "
                "daily prices does not answer the question people care about: is today's price unusually high?")
    bullets(s, 0.6, 1.5, 7.4, 5.0, [
        "Food prices in Dhaka can jump within a few weeks: onion, potato, eggs, chicken",
        "Food is more than half of what the consumer price index measures",
        "TCB (Trading Corporation of Bangladesh) publishes market prices every working day",
        "But each day is a separate sheet: it does not say whether today's price is unusual",
    ], 20)
    box(s, 8.5, 2.0, 4.2, 2.6, "The question\n\n\u201cIs today's price unusually high for this item?\u201d", 20)

    # 3 What the project does
    s = d.slide("What this project does",
                "Two things: a working monitor, and a fair test of whether machine learning helps it.")
    for i, (head, body) in enumerate([
            ("1. A daily price monitor", "For 8 everyday foods, it sets an expected highest price for each day "
                                         "and raises an alert when the price stays above it."),
            ("2. A fair test of machine learning", "Does a machine-learning model give better predictions or "
                                                   f"better alerts than a very simple rule: {same}?")]):
        x = 0.6 + i * 6.2
        box(s, x, 1.6, 5.9, 3.3, "", fill=LIGHT)
        text_box(s, x + 0.3, 1.8, 5.3, 0.6, head, 22, bold=True, color=DARK)
        text_box(s, x + 0.3, 2.55, 5.3, 2.2, body, 18)
    text_box(s, 0.6, 5.4, W - 1.2, 0.8,
             "An alert means a rise is unusual for that item. It does not say why the price rose, "
             "and it is not a forecast of future rises.", 16, italic=True, color=MUTED)

    # 4 Data
    s = d.slide("The data",
                "All prices come from TCB's daily sheets, about five and a half years of them. We checked our copy "
                "of the sheets against the originals and found no copying errors.")
    for i, (big, small) in enumerate([("8", "everyday foods"), ("1,412", "days of TCB price sheets"),
                                      ("5\u00bd years", "May 2021 to October 2026")]):
        stat(s, 0.6 + i * 4.1, 1.5, 3.85, big, small)
    text_box(s, 0.6, 3.6, W - 1.2, 0.5, "The eight foods", 20, bold=True, color=DARK)
    foods = ["Broiler chicken", "Farm eggs", "Local onion", "Potato",
             "Imported garlic", "Palm oil", "Soybean oil", "Sugar"]
    for i, f in enumerate(foods):
        col, row = i % 4, i // 4
        box(s, 0.6 + col * 3.07, 4.2 + row * 0.85, 2.85, 0.65, f, 17)
    text_box(s, 0.6, 6.0, W - 1.2, 0.5,
             "Check: 3,060 prices compared with the original sheets, no mistakes found. "
             "Missing prices are rare and are never filled in with guesses.", 15, color=MUTED)

    # 5 How an alert is raised
    s = d.slide("How an alert is raised",
                "Every day each item gets an upper limit, set a week in advance from how that item's price has "
                "moved before. One day above the limit is not enough, because one-day jumps often go away. "
                "Three days out of the last five is an alert.")
    steps = [("1", "Look back", "How much does this item's price usually move in a week?"),
             ("2", "Set a limit", "An expected highest price for each day, fixed one week before"),
             ("3", "Compare", "Is today's price above the limit?"),
             ("4", "Alert", "Above the limit on 3 of the last 5 days \u2192 alert")]
    for i, (n, head, body) in enumerate(steps):
        x = 0.6 + i * 3.1
        white_label(box(s, x + 1.05, 1.5, 0.7, 0.7, n, 20, fill=DARK, bold=True))
        text_box(s, x, 2.35, 2.8, 0.5, head, 20, bold=True, color=DARK, align=PP_ALIGN.CENTER)
        text_box(s, x, 2.9, 2.8, 1.4, body, 16, align=PP_ALIGN.CENTER)
        if i < 3:
            arrow(s, x + 1.95, 1.85, x + 4.05, 1.85)
    text_box(s, 0.6, 4.45, W - 1.2, 0.5, "Three ways of setting the limit were compared", 20, bold=True, color=DARK)
    for i, (head, body) in enumerate([("Machine learning", "A LightGBM model predicts the price"),
                                      ("Simple", "Assume the price stays the same"),
                                      ("Fixed", "Any rise of more than 7 % in a week")]):
        box(s, 0.6 + i * 4.1, 5.05, 3.85, 1.2, f"{head}\n{body}", 16)

    # 6 Testing it fairly
    s = d.slide("Testing it fairly",
                "To avoid fooling ourselves, every setting was chosen using 2024 only and saved before the later "
                "data was scored. The later period had been looked at in an earlier version of the project, so we "
                "call those results retrospective. We also compared the alerts with alerts placed on random days.")
    for t, x, w, f in [("2021 - 2023\nlearn from the past", 0.6, 4.1, LIGHT),
                       ("2024\nchoose the settings", 4.9, 3.6, RGBColor(0xD6, 0xE4, 0xF5)),
                       ("2025 - Oct 2026\ntest (retrospective)", 8.7, 4.0, RGBColor(0xFF, 0xF4, 0xD6))]:
        box(s, x, 1.6, w, 1.2, t, 18)
    bullets(s, 0.6, 3.3, W - 1.2, 3.4, [
        "Settings were chosen on 2024 and saved before the test period was scored",
        "A \u201cbig rise\u201d is defined from prices only: up 10 % or more on the price 14 report days "
        "earlier, for at least 5 report days in a row",
        "Each method is compared with the same number of alerts placed on random days",
    ], 19)

    # 7 Finding 1
    s = d.slide("Finding 1: prices rarely change",
                "On most days the price is exactly the same as the day before. Even so, there were 70 big rises "
                "over the five and a half years, mostly in onion, potato and garlic.")
    stat(s, 0.6, 1.6, 5.8, "62 - 87 %", "of days, an item's price is the same as the day before", 44)
    stat(s, 6.9, 1.6, 5.8, "70", "big rises (10 % or more, lasting) in 2021-26", 44)
    bullets(s, 0.6, 3.85, W - 1.2, 2.8, [
        "Most big rises were in onion, potato and imported garlic",
        "Palm oil, soybean oil and sugar had no big rise in 2024 or 2025-26",
    ], 19)

    # 8 Finding 2
    s = d.slide("Finding 2: machine learning did not predict better",
                "We tried two forecasting models. Neither one predicted prices better than simply saying "
                "tomorrow's price will be today's price. On prices that hardly move, today's price is the best guess.")
    box(s, 0.6, 1.6, W - 1.2, 1.5,
        f"Neither model beat {same}\nfor any time ahead, from 1 to 30 report days", 22)
    bullets(s, 0.6, 3.5, W - 1.2, 3.2, [
        "Models tried: ETS (a standard statistical method) and LightGBM (machine learning)",
        "Both were slightly worse than the simple guess, in 2024 and in 2025-26",
        "Why: the price is unchanged on most days, so a model that predicts small moves is usually wrong",
        "Adding weather and the exchange rate did not improve the predictions",
    ], 19)

    # 9 Finding 3
    s = d.slide("Finding 3: the alerts do catch big rises",
                "In 2025-26 there were 23 big rises. The machine-learning limit caught 17 and the simple limit 15, "
                "about two and a half times more than the same alerts on random days. Alerts usually came about "
                "2 report days after a rise started.")
    stat(s, 0.6, 1.6, 3.85, "17 of 23", "big rises caught: machine-learning limit (2025-26)")
    stat(s, 4.7, 1.6, 3.85, "15 of 23", "big rises caught: simple limit (2025-26)")
    stat(s, 8.8, 1.6, 3.85, "~2 days", "typical delay after a rise starts")
    bullets(s, 0.6, 3.8, W - 1.2, 3.0, [
        "About 2.5 to 2.8 times better than the same number of alerts on random days",
        "The fixed 7 % rule caught 22 of 23, but it is almost the same as the definition of a big rise, "
        "so it is not a fair winner",
        "Alerts flag rises not explained by measured cost drivers; they are not early warnings",
    ], 18)

    # 10 Finding 4
    s = d.slide("Finding 4: the simple method is enough",
                "Both limits caught almost the same rises: 15 of the 23 were caught by both. The machine-learning "
                "model adds training and upkeep but no real benefit, so the simple method is the better choice.")
    box(s, 0.6, 1.6, W - 1.2, 1.5,
        "The machine-learning limit and the simple limit caught almost the same rises\n"
        "(15 of 23 caught by both in 2025-26)", 21)
    for i, (head, body) in enumerate([("Same results", "Nearly the same rises caught"),
                                      ("No model to train", "Nothing to retrain or maintain"),
                                      ("Easy to explain", "\u201cHigher than this item usually moves in a week\u201d")]):
        box(s, 0.6 + i * 4.1, 3.5, 3.85, 1.6, f"{head}\n{body}", 17)

    # 11 App
    s = d.slide("The monitoring app",
                "A simple web app shows the result. Example: onion's price started a big rise on 2 November 2025; "
                "the app raised the alert on 4 November, two report days later.")
    bullets(s, 0.6, 1.5, 5.9, 2.6, [
        "Status on a day: all 8 items, normal or alert",
        "Item: price chart with the limit and alerts",
        "Alert log: every alert raised",
        "How it works: the methods and their scores",
    ], 17)
    text_box(s, 0.6, 4.05, 5.9, 0.5, "Example: onion, November 2025", 19, bold=True, color=DARK)
    for i, (day, t) in enumerate([("2 Nov", "Rise starts; price above the limit"),
                                  ("3 Nov", "Above again: no alert yet"),
                                  ("4 Nov", "3rd day above: alert")]):
        y = 4.6 + i * 0.7
        box(s, 0.6, y, 1.2, 0.55, day, 14, bold=True)
        text_box(s, 1.95, y, 4.6, 0.55, t, 16, anchor=MSO_ANCHOR.MIDDLE)
    picture(s, local_figs / "F5_prices_with_alerts.png", 6.9, 1.3, h=5.1)
    text_box(s, 6.9, 6.45, 5.9, 0.3, "Onion, potato and egg prices 2024-26: big rises shaded, alerts marked.",
             11, color=MUTED)

    # 12 Summary and limits
    s = d.slide("Summary and limits",
                "The main message: a daily food price monitor works, and it does not need machine learning. Be "
                "clear about the limits: the test period had been seen before, and there are few big rises.")
    text_box(s, 0.6, 1.4, 6.0, 0.5, "What we learned", 22, bold=True, color=DARK)
    bullets(s, 0.6, 2.0, 6.0, 4.7, [
        "Daily food prices in Dhaka rarely change, but big rises do happen",
        "Machine learning did not predict prices better than \u201ctomorrow = today\u201d",
        "The alerts catch most big rises, far better than chance",
        "A simple limit works as well as machine learning",
    ], 18)
    text_box(s, 7.0, 1.4, 5.7, 0.5, "Limits", 22, bold=True, color=DARK)
    bullets(s, 7.0, 2.0, 5.75, 4.7, [
        "The 2025-26 test period had been looked at in an earlier run",
        "Few big rises to test on (23 in 2025-26)",
        "Only Dhaka, only rises, past data replayed",
        "Next: connect to new TCB sheets and run it on new days",
    ], 18)

    # 13 Thank you
    s = d.slide(notes="Invite questions.")
    text_box(s, 0.8, 2.5, W - 1.6, 1.2, "Thank you", 48, bold=True, color=DARK, align=PP_ALIGN.CENTER)
    text_box(s, 0.8, 3.8, W - 1.6, 0.8, "Questions?", 28, color=TEXT, align=PP_ALIGN.CENTER)

    out.parent.mkdir(parents=True, exist_ok=True)
    d.prs.save(out)
    print(f"saved {out} ({d.n} slides)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=os.environ.get("FW_DATA_ROOT", "E:/msc_project/FoodPriceWatch_v2_local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--short", action="store_true", help="13-slide version for a shorter talk")
    ap.add_argument("--simple", action="store_true", help="plain-language version for a general audience")
    a = ap.parse_args()
    root = Path(a.data_root)
    folder = root / "reports" / "presentation"
    if a.simple:
        build_simple(root, Path(a.out) if a.out else folder / "FoodPriceWatch_presentation_simple.pptx")
    else:
        name = "FoodPriceWatch_presentation_short.pptx" if a.short else "FoodPriceWatch_presentation.pptx"
        build(root, Path(a.out) if a.out else folder / name, SHORT if a.short else None)
