import pandas as pd

import app
from xmr import analyze


def test_app_exposes_main():
    assert callable(app.main)


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


def _sample_result():
    values = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 20, 11]
    return [str(i) for i in range(len(values))], analyze(values, ruleset=1)


def test_xmr_figure_hovertemplates_carry_limit_values():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    x_tmpl = fig.data[0].hovertemplate
    assert f"{result.unpl:.2f}" in x_tmpl
    assert f"{result.x_center:.2f}" in x_tmpl
    assert f"{result.lnpl:.2f}" in x_tmpl

    mr_tmpl = fig.data[1].hovertemplate
    assert f"{result.mr_center:.2f}" in mr_tmpl
    assert f"{result.mr_upper:.2f}" in mr_tmpl


def test_xmr_figure_hlines_annotated_with_numeric_values():
    labels, result = _sample_result()
    fig = app._xmr_figure(labels, result, {}, {})

    ann_texts = {a.text for a in fig.layout.annotations}
    for value in (result.x_center, result.unpl, result.lnpl,
                  result.mr_center, result.mr_upper):
        assert f"{value:.2f}" in ann_texts
    # the abbreviations are gone
    assert "UNPL" not in ann_texts
    assert "X̄" not in ann_texts


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
