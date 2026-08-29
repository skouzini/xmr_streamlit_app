"""Streamlit UI for XmR control-chart analysis."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from xmr import MIN_POINTS, RULESETS, SOFT_LIMIT_MIN_MR, analyze

BLUE = "#1f77b4"
RED = "#d62728"
GREEN = "#2ca02c"


def clean_series(df, time_col, value_col):
    """Return (labels, values, dropped_count), keeping row order."""
    numeric = pd.to_numeric(df[value_col], errors="coerce")
    mask = numeric.notna()
    labels = df.loc[mask, time_col].astype(str).tolist()
    values = [float(v) for v in numeric[mask].tolist()]
    dropped = int((~mask).sum())
    return labels, values, dropped


def _read_upload(uploaded):
    """Return a DataFrame from an uploaded .csv or .xlsx file."""
    if uploaded.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded)
    xls = pd.ExcelFile(uploaded)
    if len(xls.sheet_names) > 1:
        sheet = st.selectbox("Sheet", xls.sheet_names)
    else:
        sheet = xls.sheet_names[0]
    return pd.read_excel(xls, sheet_name=sheet)


def _marker_colors(n, flagged_indices):
    return [RED if i in flagged_indices else BLUE for i in range(n)]


def _hover_text(n, flags_by_index):
    out = []
    for i in range(n):
        rules = sorted(flags_by_index.get(i, ()))
        if rules:
            out.append("<br>" + ", ".join(f"Rule {r}" for r in rules))
        else:
            out.append("")
    return out


def _xmr_figure(labels, result, x_flags, mr_flags):
    n = len(result.values)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "X chart (individual values)",
            "mR chart (moving ranges)",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=result.values,
            mode="lines+markers",
            line=dict(color=BLUE),
            marker=dict(color=_marker_colors(n, x_flags), size=8),
            text=_hover_text(n, x_flags),
            hovertemplate="%{x}<br>Value: %{y}%{text}<extra></extra>",
            name="Value",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(y=result.x_center, line_color=GREEN,
                  annotation_text="X̄", row=1, col=1)
    fig.add_hline(y=result.unpl, line_color=RED, line_dash="dash",
                  annotation_text="UNPL", row=1, col=1)
    fig.add_hline(y=result.lnpl, line_color=RED, line_dash="dash",
                  annotation_text="LNPL", row=1, col=1)

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=result.moving_ranges,
            mode="lines+markers",
            line=dict(color=BLUE),
            marker=dict(color=_marker_colors(n, mr_flags), size=8),
            text=_hover_text(n, mr_flags),
            hovertemplate="%{x}<br>Moving range: %{y}%{text}<extra></extra>",
            name="Moving range",
            connectgaps=False,
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=result.mr_center, line_color=GREEN,
                  annotation_text="mR̄", row=2, col=1)
    fig.add_hline(y=result.mr_upper, line_color=RED, line_dash="dash",
                  annotation_text="URL", row=2, col=1)

    fig.update_layout(height=680, showlegend=False, margin=dict(t=40, b=20))
    return fig


def main():
    st.set_page_config(page_title="XmR Chart Analyzer", layout="wide")
    st.title("XmR Chart Analyzer")

    uploaded = st.file_uploader("Upload a CSV or Excel file",
                                type=["csv", "xlsx"])
    if uploaded is None:
        st.info(
            "Upload a CSV or Excel file to begin. The repo's `sample_data.csv` "
            "is a good first try (time column `week`, value column "
            "`measurement`)."
        )
        st.stop()

    try:
        df = _read_upload(uploaded)
    except Exception as exc:  # noqa: BLE001 - surface any parser message
        st.error(f"Could not read the file: {exc}")
        st.stop()

    if df.empty or len(df.columns) < 2:
        st.error("The file needs at least two columns and one row of data.")
        st.stop()

    st.subheader("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    columns = list(df.columns)
    c1, c2 = st.columns(2)
    time_col = c1.selectbox("Time / label column", columns, index=0)
    value_col = c2.selectbox(
        "Value column", columns, index=1 if len(columns) > 1 else 0
    )
    ruleset = st.radio(
        "Detection ruleset",
        options=list(RULESETS),
        format_func=lambda r: f"Ruleset {r}  (rules {', '.join(map(str, RULESETS[r]))})",
        horizontal=True,
    )

    if time_col == value_col:
        st.error("Pick two different columns for the time and value.")
        st.stop()

    labels, values, dropped = clean_series(df, time_col, value_col)
    if dropped:
        st.warning(f"Skipped {dropped} row(s) with missing or non-numeric values.")

    if len(values) < MIN_POINTS:
        st.error(
            f"XmR charts need at least {MIN_POINTS} data points; "
            f"got {len(values)}."
        )
        st.stop()

    try:
        result = analyze(values, ruleset=ruleset)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    mr_count = sum(1 for m in result.moving_ranges if m is not None)
    if mr_count < SOFT_LIMIT_MIN_MR:
        st.warning(
            f"Only {mr_count} moving ranges available. The limits are based on "
            "limited data and should be treated as soft (provisional) until "
            f"about {SOFT_LIMIT_MIN_MR + 1} data points are available."
        )
    if result.mr_center == 0:
        st.warning(
            "Every value is identical: the moving-range average is zero and the "
            "limits collapse onto the mean."
        )

    x_flags = defaultdict(set)
    mr_flags = defaultdict(set)
    for idx, rule, chart in result.violations:
        (x_flags if chart == "x" else mr_flags)[idx].add(rule)

    st.plotly_chart(
        _xmr_figure(labels, result, x_flags, mr_flags),
        use_container_width=True,
    )

    st.subheader("Signals")
    if result.violations:
        rows = [
            {
                "Point": labels[idx],
                "Chart": "X" if chart == "x" else "mR",
                "Value": result.values[idx]
                if chart == "x"
                else result.moving_ranges[idx],
                "Rule": rule,
            }
            for idx, rule, chart in result.violations
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.success("No signals detected — the process looks predictable.")

    x_pts = len({idx for idx, _, chart in result.violations if chart == "x"})
    mr_pts = len({idx for idx, _, chart in result.violations if chart == "mr"})
    st.caption(
        f"n = {len(values)}  |  X̄ = {result.x_center:.3f}  |  "
        f"mR̄ = {result.mr_center:.3f}  |  UNPL = {result.unpl:.3f}  |  "
        f"LNPL = {result.lnpl:.3f}  |  URL = {result.mr_upper:.3f}  |  "
        f"flagged points — X: {x_pts}, mR: {mr_pts}"
    )


if __name__ == "__main__":
    main()
