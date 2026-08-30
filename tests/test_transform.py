import pandas as pd
import pytest

import transform
from transform import (
    COMBINED_VIEW,
    aggregate,
    clean_series,
    collapse_series,
    date_filter,
    parse_time,
    series_names,
    to_long,
)


# --- clean_series -----------------------------------------------------------

def test_clean_series_drops_non_numeric_and_missing_preserving_order():
    df = pd.DataFrame(
        {"t": ["a", "b", "c", "d", "e"], "v": [1, "oops", 3, None, 5]}
    )
    labels, values, dropped = clean_series(df, "t", "v")
    assert values == [1.0, 3.0, 5.0]
    assert labels == ["a", "c", "e"]
    assert dropped == 2


def test_clean_series_all_numeric():
    df = pd.DataFrame({"t": [1, 2, 3], "v": [10.0, 11.0, 12.0]})
    labels, values, dropped = clean_series(df, "t", "v")
    assert values == [10.0, 11.0, 12.0]
    assert labels == ["1", "2", "3"]
    assert dropped == 0


def test_clean_series_same_column_for_time_and_value_does_not_raise():
    df = pd.DataFrame({"v": [1, 2, 3, 4]})
    labels, values, dropped = clean_series(df, "v", "v")
    assert values == [1.0, 2.0, 3.0, 4.0]
    assert labels == ["1", "2", "3", "4"]
    assert dropped == 0


# --- aggregate -------------------------------------------------------------

def test_aggregate_week_sum_labels_by_week_start():
    df = pd.DataFrame(
        {"d": ["2026-01-05", "2026-01-07", "2026-01-12", "2026-01-14",
               "2026-01-19"],
         "v": [1, 2, 3, 4, 5]}
    )
    labels, values, dropped = aggregate(df, "d", "v", "week", "sum")
    assert dropped == 0
    assert labels == ["2026-01-05", "2026-01-12", "2026-01-19"]
    assert values == [3.0, 7.0, 5.0]


def test_aggregate_month_quarter_year():
    df = pd.DataFrame(
        {"d": ["2026-01-10", "2026-01-20", "2026-02-15", "2026-04-01",
               "2027-01-01"],
         "v": [10, 20, 30, 40, 50]}
    )
    l, v, _ = aggregate(df, "d", "v", "month", "mean")
    assert l == ["2026-01", "2026-02", "2026-04", "2027-01"]
    assert v == [15.0, 30.0, 40.0, 50.0]

    l, v, _ = aggregate(df, "d", "v", "quarter", "sum")
    assert l == ["2026-Q1", "2026-Q2", "2027-Q1"]
    assert v == [60.0, 40.0, 50.0]

    l, v, _ = aggregate(df, "d", "v", "year", "sum")
    assert l == ["2026", "2027"]
    assert v == [100.0, 50.0]


def test_aggregate_count_ignores_value_magnitude():
    df = pd.DataFrame(
        {"d": ["2026-01-05", "2026-01-06", "2026-01-12"], "v": [99, 1, 7]}
    )
    _, values, _ = aggregate(df, "d", "v", "week", "count")
    assert values == [2.0, 1.0]


def test_aggregate_drops_unparseable_date_and_value_rows():
    df = pd.DataFrame(
        {"d": ["2026-01-05", "not-a-date", "2026-01-12", "2026-01-19"],
         "v": [1, 2, "x", 4]}
    )
    _, values, dropped = aggregate(df, "d", "v", "week", "sum")
    assert dropped == 2
    assert values == [1.0, 4.0]


def test_aggregate_raises_when_column_is_not_dates():
    df = pd.DataFrame({"d": ["a", "b", "c", "d"], "v": [1, 2, 3, 4]})
    with pytest.raises(ValueError):
        aggregate(df, "d", "v", "week", "sum")


# --- parse_time ----------------------------------------------------------

def test_parse_time_parses_iso_dates():
    out = parse_time(pd.Series(["2026-01-05", "2026-02-09", "2026-03-16"]))
    assert pd.api.types.is_datetime64_any_dtype(out)
    assert out.iloc[1] == pd.Timestamp("2026-02-09")


def test_parse_time_coerces_junk_to_nat():
    out = parse_time(pd.Series(["2026-01-05", "not-a-date", ""]))
    assert out.iloc[0] == pd.Timestamp("2026-01-05")
    assert pd.isna(out.iloc[1])
    assert pd.isna(out.iloc[2])


def test_parse_time_emits_no_warning_on_mixed_input(recwarn):
    parse_time(pd.Series(["2026-01-05", "whoops", "2026-01-19"]))
    assert len(recwarn) == 0


# --- date_filter --------------------------------------------------------

def _dated(rows):
    return pd.DataFrame(rows)


def test_date_filter_both_none_returns_input_unchanged():
    df = _dated({"d": ["2026-01-05", "2026-01-12"], "v": [1, 2]})
    assert date_filter(df, "d", None, None) is df


def test_date_filter_inclusive_bounds():
    df = _dated(
        {"d": ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"],
         "v": [1, 2, 3, 4]}
    )
    out = date_filter(df, "d", pd.Timestamp("2026-01-12"),
                      pd.Timestamp("2026-01-19"))
    assert out["v"].tolist() == [2, 3]


def test_date_filter_start_only():
    df = _dated(
        {"d": ["2026-01-05", "2026-01-12", "2026-01-19"], "v": [1, 2, 3]}
    )
    out = date_filter(df, "d", pd.Timestamp("2026-01-12"), None)
    assert out["v"].tolist() == [2, 3]


def test_date_filter_end_only():
    df = _dated(
        {"d": ["2026-01-05", "2026-01-12", "2026-01-19"], "v": [1, 2, 3]}
    )
    out = date_filter(df, "d", None, pd.Timestamp("2026-01-12"))
    assert out["v"].tolist() == [1, 2]


def test_date_filter_drops_unparseable_rows_when_filtering():
    df = _dated(
        {"d": ["2026-01-05", "nope", "2026-01-19"], "v": [1, 2, 3]}
    )
    out = date_filter(df, "d", pd.Timestamp("2026-01-01"), None)
    assert out["v"].tolist() == [1, 3]


def test_date_filter_preserves_order_and_does_not_mutate_input():
    df = _dated(
        {"d": ["2026-01-19", "2026-01-05", "2026-01-12"], "v": [3, 1, 2]}
    )
    before = df.copy()
    out = date_filter(df, "d", pd.Timestamp("2026-01-05"),
                      pd.Timestamp("2026-01-19"))
    assert out["v"].tolist() == [3, 1, 2]
    pd.testing.assert_frame_equal(df, before)


def test_date_filter_applies_to_a_multi_series_long_frame():
    df = _dated(
        {"d": ["2026-01-05", "2026-01-05", "2026-01-12", "2026-01-12"],
         "site": ["a", "b", "a", "b"],
         "v": [1, 10, 2, 20]}
    )
    out = date_filter(df, "d", pd.Timestamp("2026-01-12"), None)
    assert out["v"].tolist() == [2, 20]
    assert out["site"].tolist() == ["a", "b"]


def test_aggregate_still_works_after_parse_time_refactor():
    df = pd.DataFrame(
        {"d": ["2026-01-05", "not-a-date", "2026-01-12", "2026-01-19"],
         "v": [1, 2, "x", 4]}
    )
    _, values, dropped = aggregate(df, "d", "v", "week", "sum")
    assert dropped == 2
    assert values == [1.0, 4.0]


# --- to_long -------------------------------------------------------------

def test_to_long_single_makes_one_synthetic_series():
    df = pd.DataFrame({"t": ["a", "b"], "v": [1, 2]})
    out = to_long(df, "t", ("v",), None, "single")
    assert list(out.columns) == ["time", "series", "value"]
    assert out["series"].tolist() == ["(all)", "(all)"]
    assert out["value"].tolist() == [1, 2]


def test_to_long_long_renames_and_stringifies_series():
    df = pd.DataFrame(
        {"date": ["2026-01", "2026-01", "2026-02"],
         "cat": [10, 20, 10],
         "amt": [5, 6, 7]}
    )
    out = to_long(df, "date", ("amt",), "cat", "long")
    assert out["series"].tolist() == ["10", "20", "10"]
    assert out["value"].tolist() == [5, 6, 7]
    assert out["time"].tolist() == ["2026-01", "2026-01", "2026-02"]


def test_to_long_wide_melts_columns_to_series():
    df = pd.DataFrame(
        {"d": ["2026-01", "2026-02"], "rent": [100, 100], "food": [40, 45]}
    )
    out = to_long(df, "d", ("rent", "food"), None, "wide")
    assert set(out["series"]) == {"rent", "food"}
    assert len(out) == 4
    rent = out[out["series"] == "rent"]
    assert rent["value"].tolist() == [100, 100]


def test_to_long_rejects_bad_inputs():
    df = pd.DataFrame({"d": ["x"], "v": [1], "c": ["a"]})
    with pytest.raises(ValueError):
        to_long(df, "d", ("v",), None, "sideways")
    with pytest.raises(ValueError):
        to_long(df, "d", ("v",), "d", "long")       # series col == time col
    with pytest.raises(ValueError):
        to_long(df, "d", (), None, "wide")          # no value columns
    with pytest.raises(ValueError):
        to_long(df, "d", ("missing",), None, "wide")


def test_to_long_does_not_mutate_input():
    df = pd.DataFrame({"d": ["a"], "rent": [1], "food": [2]})
    before = df.copy()
    to_long(df, "d", ("rent", "food"), None, "wide")
    pd.testing.assert_frame_equal(df, before)


# --- collapse_series --------------------------------------------------------

def _budget_long():
    return pd.DataFrame(
        {"time": ["2026-01", "2026-01", "2026-02", "2026-02", "2026-03"],
         "series": ["rent", "food", "rent", "food", "rent"],
         "value": [100, 40, 100, 45, 100]}
    )


def test_collapse_series_pick_one_filters_and_keeps_time_order():
    out = collapse_series(_budget_long(), "food")
    assert list(out.columns) == ["time", "value"]
    assert out["time"].tolist() == ["2026-01", "2026-02"]
    assert out["value"].tolist() == [40, 45]


def test_collapse_series_combined_sum_and_mean_and_count():
    s = collapse_series(_budget_long(), COMBINED_VIEW, "sum")
    assert s["time"].tolist() == ["2026-01", "2026-02", "2026-03"]
    assert s["value"].tolist() == [140.0, 145.0, 100.0]

    m = collapse_series(_budget_long(), COMBINED_VIEW, "mean")
    assert m["value"].tolist() == [70.0, 72.5, 100.0]

    c = collapse_series(_budget_long(), COMBINED_VIEW, "count")
    assert c["value"].tolist() == [2.0, 2.0, 1.0]


def test_collapse_series_combined_excludes_non_numeric():
    df = pd.DataFrame(
        {"time": ["t1", "t1", "t2"],
         "series": ["a", "b", "a"],
         "value": [10, "bad", 5]}
    )
    out = collapse_series(df, COMBINED_VIEW, "sum")
    assert out["value"].tolist() == [10.0, 5.0]


def test_collapse_series_unknown_name_raises():
    with pytest.raises(ValueError):
        collapse_series(_budget_long(), "utilities")


def test_series_names_first_appearance_order():
    assert series_names(_budget_long()) == ["rent", "food"]


def test_end_to_end_long_combined_then_month_aggregate():
    df = pd.DataFrame(
        {"d": ["2026-01-05", "2026-01-05", "2026-01-20", "2026-02-10",
               "2026-02-10", "2026-03-01", "2026-03-15", "2026-04-01"],
         "cat": ["rent", "food"] * 4,
         "amt": [100, 40, 30, 100, 45, 100, 20, 100]}
    )
    long_df = to_long(df, "d", ("amt",), "cat", "long")
    series_df = collapse_series(long_df, COMBINED_VIEW, "sum")
    labels, values, dropped = aggregate(
        series_df, "time", "value", "month", "sum"
    )
    assert labels == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert values == [170.0, 145.0, 120.0, 100.0]
    assert dropped == 0
