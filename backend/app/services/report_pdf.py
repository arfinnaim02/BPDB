"""Vector thesis figures and a seven-page evidence PDF. No fitting or database writes."""

import io
import math
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, TEAL, GREY, LIGHT = "#16343F", "#087F76", "#617780", "#E2EBE9"
MODEL_NAMES = {
    "latest_report": "Latest report (lag 2)",
    "weekly": "Same weekday (lag 7)",
    "ridge": "Ridge",
    "autoregression": "OLS (primary)",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}
KEYS = tuple(MODEL_NAMES)


def fmt(value, digits=4):
    return "-" if value is None else f"{float(value):.{digits}f}"


def text(d, x, y, value, size=11, color=NAVY, anchor="start"):
    d.add(
        String(
            x,
            y,
            str(value),
            fontName="Helvetica",
            fontSize=size,
            fillColor=colors.HexColor(color),
            textAnchor=anchor,
        )
    )


def axis(d, left, bottom, width, height, maximum, xlabels, xlabel, ylabel):
    for n in range(5):
        y = bottom + height * n / 4
        d.add(Line(left, y, left + width, y, strokeColor=colors.HexColor(LIGHT), strokeWidth=0.6))
        text(d, left - 8, y - 4, f"{maximum * n / 4:.0f}", 10, GREY, "end")
    d.add(
        Line(left, bottom, left + width, bottom, strokeColor=colors.HexColor(GREY), strokeWidth=0.8)
    )
    for position, label in xlabels:
        text(d, left + width * position, bottom - 17, label, 10, GREY, "middle")
    text(d, left, bottom + height + 13, ylabel, 10)
    text(d, left + width / 2, 7, xlabel, 10, GREY, "middle")


def line_series(d, values, left, bottom, width, height, maximum, color, markers=False):
    points = []

    def flush():
        if len(points) >= 4:
            d.add(
                PolyLine(
                    points, strokeColor=colors.HexColor(color), strokeWidth=1.15, fillColor=None
                )
            )
        elif points:
            d.add(
                Circle(
                    points[0], points[1], 1.7, fillColor=colors.HexColor(color), strokeColor=None
                )
            )

    for i, value in enumerate(values):
        if value is None:
            flush()
            points = []
            continue
        x = left + width * i / max(1, len(values) - 1)
        y = bottom + height * float(value) / maximum
        points += [x, y]
        if markers:
            d.add(Circle(x, y, 2, fillColor=colors.HexColor(color), strokeColor=None))
    flush()


def legend(d, items, y):
    x = 62
    for label, color in items:
        d.add(Line(x, y + 4, x + 18, y + 4, strokeColor=colors.HexColor(color), strokeWidth=2))
        text(d, x + 24, y, label, 10)
        x += 250


def figure(report, kind):
    d = Drawing(600, 270)
    if kind == "models":
        values = [
            r["common_dates"]["mae"]
            for key in ("validation_scores", "test_scores")
            for r in report[key]
        ]
        maximum = math.ceil(max(values) / 5) * 5
        left, width = 155, 400
        for n in range(5):
            x = left + width * n / 4
            d.add(Line(x, 38, x, 235, strokeColor=colors.HexColor(LIGHT), strokeWidth=0.6))
            text(d, x, 23, f"{maximum * n / 4:.1f}", 10, GREY, "middle")
        for i, key in enumerate(KEYS):
            y = 222 - i * 31
            text(d, left - 10, y - 3, MODEL_NAMES[key], 10, NAVY, "end")
            for offset, dataset, color in (
                (2, "validation_scores", NAVY),
                (-9, "test_scores", TEAL),
            ):
                value = next(r["common_dates"]["mae"] for r in report[dataset] if r["model"] == key)
                w = value / maximum * width
                d.add(
                    Rect(left, y + offset, w, 8, fillColor=colors.HexColor(color), strokeColor=None)
                )
                text(d, left + w + 4, y + offset - 1, fmt(value, 2), 9, color)
        legend(
            d,
            [("2024 validation (220 common dates)", NAVY), ("2025 test (287 common dates)", TEAL)],
            251,
        )
        text(d, left + width / 2, 5, "MAE (million kWh) - lower is better", 10, GREY, "middle")
    elif kind in ("daily", "monthly"):
        if kind == "daily":
            rows = report["test_predictions"]
            first, second = [r["actual"] for r in rows], [r["autoregression"] for r in rows]
            labels = [
                (i / (len(rows) - 1), r["date"][5:7])
                for i, r in enumerate(rows)
                if r["date"].endswith("-01")
            ]
            _title, xlabel, ylabel = (
                "Observed and OLS-predicted energy",
                "2025 operational month",
                "Daily energy (million kWh)",
            )
            labels = [(p, datetime(2025, int(m), 1).strftime("%b")) for p, m in labels]
            legends = [
                ("Observed target (gaps retained)", NAVY),
                ("OLS forecast (unavailable dates omitted)", TEAL),
            ]
        else:
            rows = report["test_monthly"]
            first = [
                next(s["common_dates"]["mae"] for s in r["scores"] if s["model"] == "latest_report")
                for r in rows
            ]
            second = [
                next(
                    s["common_dates"]["mae"] for s in r["scores"] if s["model"] == "autoregression"
                )
                for r in rows
            ]
            labels = [(i / 11, datetime(2025, i + 1, 1).strftime("%b")) for i in range(12)]
            _title, xlabel, ylabel = (
                "Monthly same-date error comparison",
                "2025 month (each month has its own matched sample)",
                "MAE (million kWh)",
            )
            legends = [("Exact lag-2 benchmark", NAVY), ("Primary OLS", TEAL)]
        maximum = (
            math.ceil(max(v for v in first + second if v is not None) / 50) * 50
            if kind == "daily"
            else math.ceil(max(v for v in first + second if v is not None) / 5) * 5
        )
        axis(d, 60, 43, 520, 168, max(1, maximum), labels, xlabel, ylabel)
        line_series(d, first, 60, 43, 520, 168, max(1, maximum), NAVY, kind == "monthly")
        line_series(d, second, 60, 43, 520, 168, max(1, maximum), TEAL, kind == "monthly")
        legend(d, legends, 246)
    elif kind == "scatter":
        rows = [
            r
            for r in report["test_predictions"]
            if r["actual"] is not None and all(r[k] is not None for k in KEYS)
        ]
        maximum = math.ceil(max(max(r["actual"], r["autoregression"]) for r in rows) / 50) * 50
        axis(
            d,
            60,
            43,
            190,
            190,
            maximum,
            [(i / 4, f"{maximum * i / 4:.0f}") for i in range(5)],
            "Observed energy (million kWh)",
            "OLS predicted energy (million kWh)",
        )
        d.add(
            Line(
                60,
                43,
                250,
                233,
                strokeColor=colors.HexColor(GREY),
                strokeDashArray=[4, 3],
                strokeWidth=1,
            )
        )
        for r in rows:
            d.add(
                Circle(
                    60 + 190 * r["actual"] / maximum,
                    43 + 190 * r["autoregression"] / maximum,
                    2,
                    fillColor=colors.HexColor(TEAL),
                    strokeColor=None,
                    fillOpacity=0.45,
                )
            )
        text(d, 295, 205, f"2025 matched dates: {len(rows)}", 12)
        text(d, 295, 180, "Dashed line: equal prediction", 11)
        text(d, 295, 150, "Same scale on both axes", 11)
        text(d, 295, 120, "No test-year parameter updates", 11)
    else:
        raise ValueError("Unknown figure")
    return d


def svg_bytes(report, kind):
    svg = renderSVG.drawToString(figure(report, kind))
    note = (
        f"<metadata>BPDB report {report['report_id']}; frozen snapshot "
        f"{report['source_ids']['snapshot']}; units million kWh; no model "
        f"fitting in export.</metadata>"
    )
    end = svg.index(">", svg.index("<svg")) + 1
    return (svg[:end] + note + svg[end:]).encode("utf-8")


def pdf_bytes(r):
    out = io.BytesIO()
    width = A4[0] - 96
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BodyR",
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=colors.HexColor(NAVY),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CaptionR",
            parent=styles["BodyR"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor(GREY),
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TitleR",
            parent=styles["BodyR"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeadR",
            parent=styles["BodyR"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            spaceBefore=4,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(name="CellR", parent=styles["BodyR"], fontSize=8, leading=10, spaceAfter=0)
    )
    story = []

    def p(value, style="BodyR"):
        return Paragraph(str(value), styles[style])

    def add(value, style="BodyR"):
        story.append(p(value, style))

    def heading(title):
        add(title, "HeadR")

    def table(rows, widths=None):
        body = [
            [
                p(
                    ("<font color='#FFFFFF'><b>" + escape(str(c)) + "</b></font>")
                    if i == 0
                    else escape(str(c)),
                    "CellR",
                )
                for c in row
            ]
            for i, row in enumerate(rows)
        ]
        t = Table(body, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F1F6F5")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(TEAL)),
                ]
            )
        )
        # Paragraph color overrides Table text color, so apply white header explicitly.
        for cell in body[0]:
            cell.style = ParagraphStyle(
                name="HeaderCell",
                parent=styles["CellR"],
                textColor=colors.white,
                fontName="Helvetica-Bold",
            )
        story.append(t)
        story.append(Spacer(1, 10))

    def chart(kind, display_width=width):
        d = figure(r, kind)
        scale = display_width / d.width
        d.scale(scale, scale)
        d.width *= scale
        d.height *= scale
        story.append(d)

    def next_page():
        story.append(PageBreak())

    e, s, live = r["effect"], r["study"], r["prospective"]
    generated = datetime.fromisoformat(r["generated_at"]).astimezone(timezone(timedelta(hours=6)))
    add("BPDB INTELLIGENCE", "CaptionR")
    add("Energy forecasting<br/>research evidence", "TitleR")
    add("Methods, model comparison, final-year results and prospective monitoring", "HeadR")
    add("Generated " + generated.strftime("%d %b %Y, %H:%M Bangladesh time"), "CaptionR")
    table(
        [
            ["Study target", "National daily energy generated"],
            ["Unit", "million kWh"],
            ["Development / validation / test", "2020-2023 / 2024 / 2025"],
            ["Predefined primary model", "Autoregressive OLS (not switched after testing)"],
            ["Final matched target dates", str(e["common_dates"])],
            [
                "Primary MAE / lag-2 MAE",
                f"{e['primary_mae']:.4f} / {e['baseline_mae']:.4f} million kWh",
            ],
        ],
        [180, width - 180],
    )
    heading("Main retained finding")
    add(
        (
            f"On {e['common_dates']} identical observed dates in 2025, OLS "
            f"reduced MAE by <b>{e['mae_reduction_percent']:.2f}%</b> relative "
            f"to exact lag 2. Ridge was practically tied. The tested tree "
            f"configurations did not improve this MAE comparison."
        )
    )
    heading("Interpretation boundary")
    add(
        (
            "Historical results use an explicit reporting-time assumption and "
            "current canonical revisions. They do not establish verified "
            "point-in-time availability or guarantee operational accuracy. "
            "This is research evidence supporting thesis writing, not a "
            "complete submitted thesis."
        )
    )
    add(
        (
            f"The separate prospective log currently has "
            f"<b>{live['summary']['scored_dates']} paired scored dates</b> in "
            f"its 90-day completed-target window. Pending outcomes remain "
            f"unscored; historical error is never substituted for live "
            f"accuracy."
        )
    )
    next_page()
    heading("1. Data and chronological methods")
    add(
        (
            "Original BPDB values, calendar gaps and source/version lineage "
            "are retained. Models use national daily energy only; forecasts do"
            " not become authoritative measurements."
        )
    )
    rows = [["Year", "Role", "Calendar", "Observed", "Eligible", "Held"]]
    for year, c in sorted(r["coverage"].items()):
        rows.append(
            [
                year,
                "Training"
                if int(year) < 2024
                else "Validation"
                if year == "2024"
                else "Final test",
                c["calendar"],
                c["observed"],
                c["eligible"],
                c["held"],
            ]
        )
    table(rows, [48, 105, 75, 85, 85, width - 398])
    add(
        (
            "Training-only selection used expanding full-year origins at 2021,"
            " 2022 and 2023. Learned methods shared the same nine features and"
            " fixed original previous-week donor policy. Labels and evaluation"
            " targets were never imputed; scaling was fitted within training "
            "folds."
        )
    )
    add(
        (
            f"After settings and the OLS choice were fixed, final models were "
            f"refitted once with cutoff <b>{s['test_fit_cutoff']}</b>. There "
            f"were <b>{s['fit_rows']} usable rows</b>; the actual last usable "
            f"fitting label was <b>{s['last_usable_fit_label']}</b>. Missing "
            f"labels/inputs reduce usable fitting data before the nominal "
            f"cutoff."
        )
    )
    table(
        [
            ["Feature group", "Definition"],
            ["Calendar lags", "Original lag 2, 7, 14 and 28"],
            ["Trailing summary", "Seven-day mean ending at target minus two days"],
            ["Known calendar terms", "Weekday and year sine/cosine terms"],
            ["Missing feature input", "Exact original seven days earlier; never recursive"],
            ["Issue scenario", "Noon Bangladesh on T-1; latest original input T-2"],
        ],
        [145, width - 145],
    )
    add(
        (
            f"Strict verified historical feature availability: "
            f"<b>{s['strict_historical_feature_days']}/365 test days</b>. "
            f"Unknown official publication times were assumed in that "
            f"retrospective scenario. Current prospective records instead "
            f"retain platform capture before actual issuance, while still "
            f"disclosing unknown official times."
        )
    )
    next_page()
    heading("2. Retained model comparison")
    rows = [["Method", "2024 MAE", "2024 RMSE", "2025 MAE", "2025 RMSE"]]
    for key in KEYS:
        a = next(x["common_dates"] for x in r["validation_scores"] if x["model"] == key)
        b = next(x["common_dates"] for x in r["test_scores"] if x["model"] == key)
        rows.append(
            [MODEL_NAMES[key], fmt(a["mae"]), fmt(a["rmse"]), fmt(b["mae"]), fmt(b["rmse"])]
        )
    table(rows, [155, 86, 86, 86, width - 413])
    chart("models")
    add(
        (
            "Figure 1. MAE starts at zero. Validation compares 220 identical "
            "dates; final test compares 287 identical dates. Units are million"
            " kWh. Different years/samples and refitted models mean this is "
            "not a paired year-to-year test."
        ),
        "CaptionR",
    )
    add(
        (
            "The OLS primary choice preceded final scoring. The tiny Ridge/OLS"
            " difference is not meaningful evidence of superiority and did not"
            " trigger post-test switching. These are bounded model-family "
            "comparisons, not an exhaustive search."
        )
    )
    add(
        (
            "Calendar forecasts in 2025: OLS/Ridge/trees 311 of 365; exact lag"
            " 2: 328; exact lag 7: 327. OLS can be scored on 303 own available"
            " target dates. Own-date errors use different samples and are not "
            "the fair head-to-head scores shown here."
        )
    )
    next_page()
    heading("3. Temporal results and forecast errors")
    chart("daily")
    add(
        (
            "Figure 2. Frozen 2025 original eligible targets and OLS forecasts"
            " on the dense calendar. Missing targets and unavailable forecasts"
            " remain gaps; no lines bridge missing observations."
        ),
        "CaptionR",
    )
    chart("monthly")
    add(
        (
            "Figure 3. Monthly MAE on the all-six-method common-date "
            "intersection within each month. Monthly denominators differ. This"
            " is descriptive error variation, not further tuning or evidence "
            "of a causal seasonal effect."
        ),
        "CaptionR",
    )
    next_page()
    heading("4. Matched-date calibration and sensitivity")
    chart("scatter")
    add(
        (
            "Figure 4. The same 287 matched 2025 dates. Dashed diagonal "
            "denotes equal prediction, not a fitted calibration line or a "
            "forecast interval. Primary signed bias is about -4.5085 million "
            "kWh."
        ),
        "CaptionR",
    )
    rows = [["Month", "Common dates", "Lag-2 MAE", "OLS MAE"]]
    for month in r["test_monthly"]:
        a = next(x["common_dates"] for x in month["scores"] if x["model"] == "latest_report")
        b = next(x["common_dates"] for x in month["scores"] if x["model"] == "autoregression")
        rows.append([month["month"], b["n"], fmt(a["mae"]), fmt(b["mae"])])
    table(rows, [105, 110, 140, width - 355])
    rows = [["Calendar block", "MAE difference", "2.5th percentile", "97.5th percentile"]]
    for row in r["paired_sensitivity"]:
        rows.append(
            [
                str(row["block_days"]) + " days",
                fmt(row["point_difference"]),
                fmt(row["lower_2_5"]),
                fmt(row["upper_97_5"]),
            ]
        )
    table(rows, [110, 125, 130, width - 365])
    add(
        (
            "Paired OLS-minus-lag-2 absolute-error contrast; 2,000 circular "
            "calendar-block resamples per length, with missing/unmatched rows "
            "retained. Negative differences favor OLS. These are descriptive "
            "dependence-sensitivity ranges, not future prediction intervals or"
            " calibrated significance tests."
        ),
        "CaptionR",
    )
    next_page()
    heading("5. Prospective monitoring - separate evidence")
    summary = live["summary"]
    add(
        (
            f"Completed-target window: {summary['window_start']} to "
            f"{summary['window_end']}. The log starts with real retained "
            f"issues; no historical predictions are backfilled."
        )
    )
    table(
        [
            ["Target dates attempted", "Dates with a forecast", "Paired scored dates"],
            [
                summary["completed_targets_attempted"],
                summary["completed_targets_with_forecast"],
                summary["scored_dates"],
            ],
        ],
        [width / 3] * 3,
    )
    table(
        [
            ["Prospective MAE", "Prospective RMSE", "Prospective bias"],
            [fmt(summary["mae"]), fmt(summary["rmse"]), fmt(summary["bias"])],
        ],
        [width / 3] * 3,
    )
    add(
        (
            "When there are no paired outcomes, error values are unavailable "
            "rather than zero. A small sample is not evidence of reliability. "
            "The summary chooses the earliest successful issue per target and "
            "its latest retained actual revision, never a later forecast "
            "selected for lower error."
        )
    )
    rows = [["Target", "Issued (BDT)", "Status", "Predicted", "Actual", "Abs. error"]]
    for row in live["items"][:8]:
        issued = (
            datetime.fromisoformat(row["issued_at"])
            .astimezone(timezone(timedelta(hours=6)))
            .strftime("%d %b %H:%M")
        )
        actual = row["outcome"] or {}
        rows.append(
            [
                row["target_date"],
                issued,
                row["status"],
                fmt(row["prediction"], 3),
                fmt(actual.get("observed"), 3),
                fmt(actual.get("absolute_error"), 3),
            ]
        )
    if len(rows) > 1:
        table(rows, [80, 94, 75, 85, 85, width - 419])
    else:
        add("No retained forecast issues are available in this snapshot.")
    add(
        (
            "Latest eight attempts are shown above; the JSON contains up to "
            "100 attempts and all first-issue summary evidence for its 90-day "
            "window. Pending actuals/errors remain blank in numerical exports."
            " Withheld attempts retain a reason rather than an invented "
            "prediction."
        ),
        "CaptionR",
    )
    add(
        (
            "Prospective inputs are captured in Neon before actual issue time."
            " Known future timestamps are excluded; official publication times"
            " may remain unknown. Identical reruns preserve the original "
            "issue/time; changed inputs create another retained attempt. "
            "Eligible actual revisions are appended only after the target day "
            "ends."
        )
    )
    add(
        (
            f"Saved model: {live['model']['family']}; "
            f"{live['model']['fit_rows']} usable fitting rows; last usable "
            f"label {live['model']['last_fit_label']}. It is not silently "
            f"retrained. Historical 2025 MAE is not substituted for prospective "
            f"accuracy."
        )
    )
    next_page()
    heading("6. Provenance, limits and reproducibility")
    add(
        "Current database inventory is separate from the frozen modelling sample: "
        + str(r["current_inventory"]["canonical_dates"])
        + " canonical dates, "
        + str(r["current_inventory"]["earliest_operational_date"])
        + " through "
        + str(r["current_inventory"]["latest_operational_date"])
        + ". Missing canonical dates do not prove missing official reports.",
        "CaptionR",
    )
    for name, value in {"Report snapshot": r["report_id"], **r["source_ids"]}.items():
        add(
            escape(name)
            + ":<br/><font name='Courier' size='7'>"
            + value[:32]
            + "<br/>"
            + value[32:]
            + "</font>",
            "CaptionR",
        )
    add(
        (
            "Report ID binds data, retained-source identities and report code;"
            " it excludes only generation time. It is not a checksum of the "
            "PDF bytes. Preserve the downloaded JSON alongside the PDF and "
            "figures."
        ),
        "CaptionR",
    )
    heading("Limits that accompany every result")
    for value in r["limitations"][:6]:
        add("- " + escape(value), "CaptionR")
    add(
        (
            "This is not a complete literature review, institution-specific "
            "thesis, independent original-PDF audit or operational "
            "certification. Further model development cannot reuse 2025 as a "
            "fresh untouched holdout."
        ),
        "CaptionR",
    )
    add(
        (
            "References: BPDB daily-generation archive (misc.bpdb.gov.bd); "
            "Forecasting: Principles and Practice - forecast evaluation "
            "(otexts.com/fpp3/toolbox.html); scikit-learn common pitfalls - "
            "preprocessing; arch time-series bootstrap documentation. Full "
            "URLs and source identifiers accompany the methods/results "
            "Markdown export."
        ),
        "CaptionR",
    )

    from app.services.research_detail import append_pdf

    append_pdf(r, next_page, heading, add, table)

    def page(canvas, doc):
        canvas.saveState()
        canvas.setTitle("BPDB energy forecasting research report")
        canvas.setAuthor("BPDB Intelligence")
        canvas.setSubject("Research report snapshot " + r["report_id"])
        canvas.setStrokeColor(colors.HexColor(TEAL))
        canvas.setLineWidth(1)
        canvas.line(48, A4[1] - 35, A4[0] - 48, A4[1] - 35)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor(GREY))
        canvas.drawString(48, 23, "BPDB Intelligence | Research evidence | " + r["report_id"][:12])
        canvas.drawRightString(A4[0] - 48, 23, f"{doc.page} / 18")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=43,
        title="BPDB energy forecasting research report",
        author="BPDB Intelligence",
    )
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return out.getvalue()
