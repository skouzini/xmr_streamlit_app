import pandas as pd

import app
from xmr import analyze


def _inputs(df, time_col="t", value_col="v", ruleset=1,
            x_center="mean", mr_center="mean", is_sample=False):
    return app.Inputs(df, time_col, value_col, ruleset,
                      x_center, mr_center, is_sample)


def test_app_exposes_main():
    assert callable(app.main)


def test_bundled_sample_matches_the_csv_file():
    from pathlib import Path

    on_disk = (Path(app.__file__).parent / "sample_data.csv").read_text()
    assert app.SAMPLE_CSV == on_disk


def test_sample_df_parses_and_charts_cleanly():
    df = app._sample_df()
    assert list(df.columns) == ["week", "measurement"]
    assert len(df) == 24

    labels, values, dropped = app.clean_series(df, "week", "measurement")
    assert dropped == 0
    result = analyze(values, ruleset=1)
    assert result.violations  # the sample is built to trip at least one rule


def test_data_tab_renders_a_preview_not_the_whole_table(monkeypatch):
    shown = []
    monkeypatch.setattr(app.st, "dataframe", lambda *a, **k: shown.append(a[0]))
    captions = []
    monkeypatch.setattr(app.st, "caption", lambda *a, **k: captions.append(a[0]))

    df = pd.DataFrame({"t": range(200), "v": range(200)})
    app._render_data_tab(_inputs(df))

    assert len(shown) == 1
    assert len(shown[0]) == app.PREVIEW_ROWS
    assert f"first {app.PREVIEW_ROWS} rows" in captions[0]


def test_data_tab_renders_regardless_of_column_choice(monkeypatch):
    shown = []
    monkeypatch.setattr(app.st, "dataframe", lambda *a, **k: shown.append(a))
    monkeypatch.setattr(app.st, "caption", lambda *a, **k: None)

    df = pd.DataFrame({"v": [1, 2, 3, 4]})
    app._render_data_tab(_inputs(df, "v", "v"))  # same column — still shows
    assert len(shown) == 1


def test_ruleset_help_summarizes_every_rule_in_each_ruleset():
    from xmr import RULESETS

    help_text = app._ruleset_help()
    for rs, rules in RULESETS.items():
        assert f"Ruleset {rs}" in help_text
        for r in rules:
            assert app.RULE_SUMMARIES[r] in help_text


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
    app._render_charts_tab(_inputs(good))
    assert len(drawn) == 1

    drawn.clear()
    app._render_charts_tab(_inputs(good, "t", "t"))    # same column
    app._render_charts_tab(_inputs(pd.DataFrame({"a": ["x"], "b": ["y"]}),
                                   "a", "b"))
    assert drawn == []  # error paths return without drawing


def test_summary_caption_and_hover_relabel_for_median():
    labels = [str(i) for i in range(12)]
    values = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 20, 11]
    r = analyze(values, ruleset=1, x_center="median", mr_center="median")

    caption = app._summary_caption(r, len(values))
    assert "X̃ =" in caption and "mR̃ =" in caption
    assert "X̄" not in caption and "mR̄" not in caption

    fig = app._xmr_figure(labels, r, {}, {})
    x_tmpl, mr_tmpl = (t.hovertemplate for t in _line_traces(fig))
    assert "X̃" in x_tmpl and "mR̃" in mr_tmpl

    r_mean = analyze(values, ruleset=1)
    assert "X̄ =" in app._summary_caption(r_mean, len(values))


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


def test_xmr_figure_hovertemplates_list_limits_one_per_line_high_to_low():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})
    x_tmpl, mr_tmpl = (t.hovertemplate for t in _line_traces(fig))

    assert f"<br>UNPL {result.unpl:.2f}" in x_tmpl
    assert f"<br>X̄ {result.x_center:.2f}" in x_tmpl
    assert f"<br>LNPL {result.lnpl:.2f}" in x_tmpl
    # ordered highest value on top
    assert x_tmpl.index("UNPL") < x_tmpl.index("X̄") < x_tmpl.index("LNPL")

    assert f"<br>URL {result.mr_upper:.2f}" in mr_tmpl
    assert f"<br>mR̄ {result.mr_center:.2f}" in mr_tmpl
    assert mr_tmpl.index("URL") < mr_tmpl.index("mR̄")


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
