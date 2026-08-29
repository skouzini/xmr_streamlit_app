import pandas as pd

import app


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
