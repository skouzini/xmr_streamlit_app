"""Streamlit UI for XmR control-chart analysis."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from xmr import MIN_POINTS, RULESETS, SOFT_LIMIT_MIN_MR, analyze

RED = "#d62728"  # signal-point highlight
PREVIEW_ROWS = 50  # rows shown in the Data tab preview

# One-line summary of each detection rule, for the ruleset tooltip.
RULE_SUMMARIES = {
    1: "a single point outside the limits (3σ)",
    2: "8 consecutive points on one side of the centerline",
    3: "3 of 4 points beyond 1.5σ, same side",
    4: "2 of 3 points beyond 2σ, same side",
    5: "4 of 5 points beyond 1σ, same side",
}

# One neutral-gray palette that reads on both light and dark backgrounds.
# Same hue throughout; opacity is the contrast ramp — trend line loudest,
# then centerline, then the 3-sigma limits, then the secondary zone lines.
TREND_COLOR = "#808080"
CENTER_COLOR = "rgba(128, 128, 128, 0.7)"
LIMIT_COLOR = "rgba(128, 128, 128, 0.4)"
ZONE_COLOR = "rgba(128, 128, 128, 0.28)"
GRID_COLOR = "rgba(128, 128, 128, 0.15)"


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


def _hover_text(n, flags_by_index):
    out = []
    for i in range(n):
        rules = sorted(flags_by_index.get(i, ()))
        if rules:
            out.append("<br>" + ", ".join(f"Rule {r}" for r in rules))
        else:
            out.append("")
    return out


def _signal_points(labels, y_values, flags_by_index):
    """(xs, ys) for the flagged indices only — the red dots."""
    idx = sorted(i for i in flags_by_index if flags_by_index[i])
    return [labels[i] for i in idx], [y_values[i] for i in idx]


def _line_and_signals(fig, row, labels, y_values, flags, hovertemplate, n):
    """Add the grey trend line plus a red markers-only trace for signals."""
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=y_values,
            mode="lines",
            line=dict(color=TREND_COLOR, width=1.5),
            text=_hover_text(n, flags),
            hovertemplate=hovertemplate,
            connectgaps=False,
            showlegend=False,
        ),
        row=row,
        col=1,
    )
    sig_x, sig_y = _signal_points(labels, y_values, flags)
    fig.add_trace(
        go.Scatter(
            x=sig_x,
            y=sig_y,
            mode="markers",
            marker=dict(color=RED, size=9),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def _labeled_hline(fig, row, y, color, dash, position):
    fig.add_hline(
        y=y, line_color=color, line_dash=dash, line_width=1,
        annotation_text=f"{y:.2f}", annotation_position=position,
        annotation_font_size=10, row=row, col=1,
    )


def _xmr_figure(labels, result, x_flags, mr_flags):
    n = len(result.values)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
    )

    x_hover = (
        "%{x}<br>Value: %{y}%{text}"
        f"<br>UNPL {result.unpl:.2f}"
        f"<br>X̄ {result.x_center:.2f}"
        f"<br>LNPL {result.lnpl:.2f}"
        "<extra></extra>"
    )
    _line_and_signals(fig, 1, labels, result.values, x_flags, x_hover, n)

    # secondary detection zones for the active ruleset (very faint, unlabeled)
    for y in result.x_zone_bounds:
        fig.add_hline(y=y, line_color=ZONE_COLOR, line_dash="dot",
                      line_width=1, row=1, col=1)
    _labeled_hline(fig, 1, result.x_center, CENTER_COLOR, "solid", "top right")
    _labeled_hline(fig, 1, result.unpl, LIMIT_COLOR, "dash", "top right")
    _labeled_hline(fig, 1, result.lnpl, LIMIT_COLOR, "dash", "bottom right")

    mr_hover = (
        "%{x}<br>Moving range: %{y}%{text}"
        f"<br>URL {result.mr_upper:.2f}"
        f"<br>mR̄ {result.mr_center:.2f}"
        "<extra></extra>"
    )
    _line_and_signals(fig, 2, labels, result.moving_ranges, mr_flags, mr_hover, n)
    _labeled_hline(fig, 2, result.mr_center, CENTER_COLOR, "solid", "top right")
    _labeled_hline(fig, 2, result.mr_upper, LIMIT_COLOR, "dash", "top right")

    # x-axis tick labels on the X chart (row 1), not the mR chart (row 2)
    fig.update_xaxes(showticklabels=True, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    # chart names as rotated (vertical) y-axis titles
    fig.update_yaxes(title_text="X chart (individual values)", row=1, col=1)
    fig.update_yaxes(title_text="mR chart (moving ranges)", row=2, col=1)

    fig.update_layout(height=680, showlegend=False, margin=dict(t=20, b=20),
                      hovermode="closest")
    return fig


def _signals_table_rows(result, labels):
    return [
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


def _summary_caption(result, n):
    x_pts = len({idx for idx, _, chart in result.violations if chart == "x"})
    mr_pts = len({idx for idx, _, chart in result.violations if chart == "mr"})
    return (
        f"n = {n}  |  X̄ = {result.x_center:.3f}  |  "
        f"mR̄ = {result.mr_center:.3f}  |  UNPL = {result.unpl:.3f}  |  "
        f"LNPL = {result.lnpl:.3f}  |  URL = {result.mr_upper:.3f}  |  "
        f"flagged points — X: {x_pts}, mR: {mr_pts}"
    )


def _sidebar_inputs():
    """Render the sidebar controls.

    Returns ``(df, time_col, value_col, ruleset)`` once a usable file is
    uploaded, or ``None`` when nothing has been uploaded yet. Calls
    ``st.stop()`` itself for an unreadable or malformed file.
    """
    with st.sidebar:
        st.header("Data & options")
        uploaded = st.file_uploader(
            "Upload a CSV or Excel file", type=["csv", "xlsx"]
        )
        if uploaded is None:
            st.caption("`sample_data.csv` in the repo is a good first try.")
            return None

        try:
            df = _read_upload(uploaded)
        except Exception as exc:  # noqa: BLE001 - surface any parser message
            st.error(f"Could not read the file: {exc}")
            st.stop()

        if df.empty or len(df.columns) < 2:
            st.error("The file needs at least two columns and one row of data.")
            st.stop()

        columns = list(df.columns)
        time_col = st.selectbox("Time / label column", columns, index=0)
        value_col = st.selectbox(
            "Value column", columns, index=1 if len(columns) > 1 else 0
        )
        ruleset = st.radio(
            "Detection ruleset",
            options=list(RULESETS),
            format_func=lambda r: (
                f"Ruleset {r} — rules {', '.join(map(str, RULESETS[r]))}"
            ),
            help=_ruleset_help(),
        )
    return df, time_col, value_col, ruleset


def _ruleset_help():
    """Markdown summary of each ruleset's detection rules, for the tooltip."""
    blocks = []
    for rs, rules in RULESETS.items():
        items = "\n".join(f"- **{r}.** {RULE_SUMMARIES[r]}" for r in rules)
        blocks.append(f"**Ruleset {rs}**\n{items}")
    return "\n\n".join(blocks)


def main():
    st.set_page_config(
        page_title="XmR Chart Analyzer",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("XmR Chart Analyzer")

    inputs = _sidebar_inputs()
    if inputs is None:
        st.info(
            "Upload a CSV or Excel file from the sidebar to begin. The repo's "
            "`sample_data.csv` is a good first try (time column `week`, value "
            "column `measurement`)."
        )
        st.stop()
    df, time_col, value_col, ruleset = inputs

    charts_tab, data_tab = st.tabs(["📈 Charts", "🗂 Data"])

    # The Data tab always renders — even when the column choice can't produce a
    # chart yet, so you can look at the file and pick the right columns.
    with data_tab:
        _render_data_tab(df, time_col, value_col)

    with charts_tab:
        _render_charts_tab(df, time_col, value_col, ruleset)


def _render_data_tab(df, time_col, value_col):
    _, values, dropped = clean_series(df, time_col, value_col)
    note = f"{len(df)} rows uploaded · {len(values)} usable in `{value_col}`"
    if dropped:
        note += f" · {dropped} skipped (missing or non-numeric)"
    if len(df) > PREVIEW_ROWS:
        note += f" · preview: first {PREVIEW_ROWS} rows"
    st.caption(note)
    st.dataframe(df.head(PREVIEW_ROWS), use_container_width=True)


def _render_charts_tab(df, time_col, value_col, ruleset):
    if time_col == value_col:
        st.error(
            "Pick two different columns for the time and value "
            "(check the **Data** tab)."
        )
        return

    labels, values, dropped = clean_series(df, time_col, value_col)
    if dropped:
        st.warning(
            f"Skipped {dropped} row(s) with missing or non-numeric values."
        )

    if len(values) < MIN_POINTS:
        st.error(
            f"XmR charts need at least {MIN_POINTS} data points; "
            f"got {len(values)} usable in `{value_col}` — check the **Data** tab."
        )
        return

    try:
        result = analyze(values, ruleset=ruleset)
    except ValueError as exc:
        st.error(str(exc))
        return

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
        st.dataframe(
            pd.DataFrame(_signals_table_rows(result, labels)),
            use_container_width=True,
        )
    else:
        st.success("No signals detected — the process looks predictable.")
    st.caption(_summary_caption(result, len(values)))


if __name__ == "__main__":
    main()
