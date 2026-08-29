import pandas as pd

import app
from xmr import analyze


def test_app_exposes_main():
    assert callable(app.main)


def test_data_tab_renders_regardless_of_column_choice(monkeypatch):
    shown = []
    monkeypatch.setattr(app.st, "dataframe", lambda *a, **k: shown.append(a))
    monkeypatch.setattr(app.st, "caption", lambda *a, **k: None)

    df = pd.DataFrame({"v": [1, 2, 3, 4]})
    app._render_data_tab(df, "v", "v")  # same column picked — still shows
    assert len(shown) == 1


def test_charts_tab_draws_a_chart_only_when_the_data_is_usable(monkeypatch):
    drawn = []
    monkeypatch.setattr(app.st, "plotly_chart", lambda *a, **k: drawn.append(a))
    for name in ("error", "warning", "success", "subheader", "caption",
                 "dataframe"):
        monkeypatch.setattr(app.st, name, lambda *a, **k: None)

    good = pd.DataFrame(
        {"t": list(range(12)),
         "v": [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 20, 11]}
    )
    app._render_charts_tab(good, "t", "v", 1)
    assert len(drawn) == 1

    drawn.clear()
    app._render_charts_tab(good, "t", "t", 1)          # same column
    app._render_charts_tab(pd.DataFrame({"a": ["x"], "b": ["y"]}), "a", "b", 1)
    assert drawn == []  # error paths return without drawing


def test_clean_series_drops_non_numeric_and_missing_preserving_order():
    df = pd.DataFrame(
        {"t": ["a", "b", "c", "d", "e"], "v": [1, "oops", 3, None, 5]}
    )
    labels, values, dropped = app.clean_series(df, "t", "v")
    assert values == [1.0, 3.0, 5.0]
    assert labels == ["a", "c", "e"]
    assert dropped == 2


def test_clean_series_all_numeric():
    df = pd.DataFrame({"t": [1, 2, 3], "v": [10.0, 11.0, 12.0]})
    labels, values, dropped = app.clean_series(df, "t", "v")
    assert values == [10.0, 11.0, 12.0]
    assert labels == ["1", "2", "3"]
    assert dropped == 0


def test_clean_series_same_column_for_time_and_value_does_not_raise():
    df = pd.DataFrame({"v": [1, 2, 3, 4]})
    labels, values, dropped = app.clean_series(df, "v", "v")
    assert values == [1.0, 2.0, 3.0, 4.0]
    assert labels == ["1", "2", "3", "4"]
    assert dropped == 0


def _sample_result(ruleset=1):
    values = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 20, 11]
    return [str(i) for i in range(len(values))], analyze(values, ruleset=ruleset)


def _line_traces(fig):
    return [t for t in fig.data if t.mode == "lines"]


def _marker_traces(fig):
    return [t for t in fig.data if t.mode == "markers"]


def test_xmr_figure_hovertemplates_carry_limit_values():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    x_tmpl, mr_tmpl = (t.hovertemplate for t in _line_traces(fig))
    assert f"{result.unpl:.2f}" in x_tmpl
    assert f"{result.x_center:.2f}" in x_tmpl
    assert f"{result.lnpl:.2f}" in x_tmpl
    assert f"{result.mr_center:.2f}" in mr_tmpl
    assert f"{result.mr_upper:.2f}" in mr_tmpl


def test_xmr_figure_hlines_annotated_with_numeric_values_on_the_right():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    ann_texts = {a.text for a in fig.layout.annotations}
    for value in (result.x_center, result.unpl, result.lnpl,
                  result.mr_center, result.mr_upper):
        assert f"{value:.2f}" in ann_texts
    assert "UNPL" not in ann_texts
    assert "X̄" not in ann_texts
    # numbers sit on the right (zone lines add no annotations)
    assert {a.xanchor for a in fig.layout.annotations} == {"right"}


def test_xmr_figure_non_signal_points_have_no_dots():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {10: {1}}, {10: {1}})

    # the data traces are pure lines, no markers
    for t in _line_traces(fig):
        assert t.mode == "lines"
        assert t.marker.color is None

    # signal dots are a separate red markers-only trace per chart
    marker_traces = _marker_traces(fig)
    assert len(marker_traces) == 2
    for t in marker_traces:
        assert t.marker.color == app.RED
        assert list(t.x) == ["10"]
        assert t.hoverinfo == "skip"


def test_xmr_figure_trend_and_line_colors_are_a_fixed_gray_ramp():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    for t in _line_traces(fig):
        assert t.line.color == app.TREND_COLOR
    shape_colors = {s.line.color for s in fig.layout.shapes}
    assert app.CENTER_COLOR in shape_colors   # centerline
    assert app.LIMIT_COLOR in shape_colors    # 3-sigma limits
    assert app.ZONE_COLOR in shape_colors     # secondary zones
    # opacity ramp: trend solid, centerline darker than limits, zones faintest
    assert "0.7" in app.CENTER_COLOR
    assert "0.4" in app.LIMIT_COLOR
    assert "0.28" in app.ZONE_COLOR


def test_signals_table_rows_map_violations_to_labels():
    labels, result = _sample_result()
    rows = app._signals_table_rows(result, labels)

    assert len(rows) == len(result.violations)
    for row, (idx, rule, chart) in zip(rows, result.violations):
        assert row["Point"] == labels[idx]
        assert row["Chart"] == ("X" if chart == "x" else "mR")
        assert row["Rule"] == rule
        expected = (
            result.values[idx] if chart == "x" else result.moving_ranges[idx]
        )
        assert row["Value"] == expected


def test_summary_caption_reports_limits_and_split_counts():
    labels, result = _sample_result()
    caption = app._summary_caption(result, len(result.values))

    assert f"n = {len(result.values)}" in caption
    assert f"UNPL = {result.unpl:.3f}" in caption
    assert "flagged points — X:" in caption


def test_xmr_figure_secondary_zone_line_count_matches_ruleset():
    labels, r1 = _sample_result(ruleset=1)
    labels, r2 = _sample_result(ruleset=2)
    fig1 = app._xmr_figure(labels, r1, {}, {})
    fig2 = app._xmr_figure(labels, r2, {}, {})

    zone1 = [s for s in fig1.layout.shapes if s.line.color == app.ZONE_COLOR]
    zone2 = [s for s in fig2.layout.shapes if s.line.color == app.ZONE_COLOR]
    assert len(zone1) == 2   # +/- 1.5 sigma
    assert len(zone2) == 4   # +/- 1 sigma and +/- 2 sigma


def test_xmr_figure_x_axis_on_x_chart_only():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    assert fig.layout.xaxis.showticklabels is True
    assert fig.layout.xaxis2.showticklabels is False


def test_xmr_figure_titles_are_y_axis_titles():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    assert fig.layout.yaxis.title.text == "X chart (individual values)"
    assert fig.layout.yaxis2.title.text == "mR chart (moving ranges)"
    assert fig.layout.annotations is not None  # subplot_titles removed, hline anns remain
