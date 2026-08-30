"""Pure data-shaping helpers for the XmR app.

No Streamlit import here — these functions are unit-tested in isolation.
They turn an uploaded table into the ordered ``(labels, values)`` sequence
that ``xmr.analyze`` expects.
"""

from __future__ import annotations

import re
import warnings

import pandas as pd

from xmr import MIN_POINTS

GRANULARITIES = ("raw", "day", "week", "month", "quarter", "year")
_QUARTER_LABEL = re.compile(r"^\s*(\d{4})-Q([1-4])\s*$")
AGGFUNCS = ("sum", "mean", "median", "min", "max", "count", "first", "last")
COMBINE_FUNCS = ("sum", "mean", "min", "max", "count")
LAYOUTS = ("single", "long", "wide")
COMBINED_VIEW = "Combined"
_ALL_SERIES = "(all)"
_PERIOD_CODE = {"day": "D", "week": "W", "month": "M", "quarter": "Q",
                "year": "Y"}


def parse_time(series):
    """``pd.to_datetime(series, errors="coerce")`` with the "could not infer
    format" ``UserWarning`` suppressed.

    Returns a ``datetime64`` Series, ``NaT`` where a value doesn't parse.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.to_datetime(series, errors="coerce")


def date_filter(df, time_col, start=None, end=None):
    """Restrict ``df`` to rows whose parsed ``time_col`` falls within
    ``[start, end]`` inclusive.

    ``start`` / ``end`` are ``date`` / ``Timestamp`` or ``None`` (that bound
    open). With both ``None`` the input frame is returned unchanged (rows
    whose time doesn't parse are kept). Otherwise unparseable rows are
    dropped. Row order is preserved; the input is not mutated.
    """
    if start is None and end is None:
        return df
    times = parse_time(df[time_col])
    mask = times.notna()
    if start is not None:
        mask &= times >= pd.Timestamp(start)
    if end is not None:
        mask &= times <= pd.Timestamp(end)
    return df[mask.to_numpy()]


def _label_timestamp(label):
    """Parse one x-axis label to a Timestamp (``NaT`` if it doesn't parse).

    Handles the ``YYYY-Qn`` labels ``aggregate`` emits (which ``parse_time``
    can't) plus everything ``parse_time`` handles: ``YYYY``, ``YYYY-MM``,
    ``YYYY-MM-DD`` and raw date passthroughs.
    """
    m = _QUARTER_LABEL.match(str(label))
    if m:
        year, quarter = int(m.group(1)), int(m.group(2))
        return pd.Timestamp(year=year, month=(quarter - 1) * 3 + 1, day=1)
    return parse_time(pd.Series([label])).iloc[0]


def baseline_index_range(labels, start, end):
    """Translate a date window to a half-open index range over ``labels``.

    ``labels`` are the x-axis strings ``clean_series`` / ``aggregate`` produce.
    ``start`` / ``end`` are ``date`` / ``Timestamp`` (inclusive). Returns
    ``(i0, i1)`` spanning the labels that fall in the window. Raises
    ``ValueError`` when fewer than ``MIN_POINTS`` labels land inside it.
    """
    lo = pd.Timestamp(start) if start is not None else None
    hi = pd.Timestamp(end) if end is not None else None
    inside = []
    for i, label in enumerate(labels):
        t = _label_timestamp(label)
        if pd.isna(t):
            continue
        if (lo is None or t >= lo) and (hi is None or t <= hi):
            inside.append(i)
    if len(inside) < MIN_POINTS:
        raise ValueError(
            f"The baseline window covers {len(inside)} point(s); "
            f"XmR needs at least {MIN_POINTS}."
        )
    return inside[0], inside[-1] + 1


def clean_series(df, time_col, value_col):
    """Return (labels, values, dropped_count), keeping row order."""
    numeric = pd.to_numeric(df[value_col], errors="coerce")
    mask = numeric.notna()
    labels = df.loc[mask, time_col].astype(str).tolist()
    values = [float(v) for v in numeric[mask].tolist()]
    dropped = int((~mask).sum())
    return labels, values, dropped


def _period_label(period, granularity):
    if granularity == "quarter":
        return f"{period.year}-Q{period.quarter}"
    if granularity == "year":
        return str(period.year)
    if granularity == "month":
        return period.strftime("%Y-%m")
    if granularity == "week":
        return period.start_time.strftime("%Y-%m-%d")
    return period.strftime("%Y-%m-%d")


def aggregate(df, time_col, value_col, granularity, aggfunc):
    """Resample df to a calendar granularity.

    Returns ``(labels, values, dropped)`` — the same shape as ``clean_series``.
    Rows whose time doesn't parse as a date, or whose value isn't numeric, are
    dropped and counted. Raises ``ValueError`` when fewer than two rows have a
    usable date (the time column isn't dates).
    """
    # non-date strings coerce to NaT and are handled below.
    dates = parse_time(df[time_col])
    nums = pd.to_numeric(df[value_col], errors="coerce")
    mask = dates.notna() & nums.notna()
    dropped = int((~mask).sum())
    if int(mask.sum()) < 2:
        raise ValueError(f"Time column {time_col!r} doesn't look like dates.")

    sub = pd.DataFrame(
        {"period": dates[mask].dt.to_period(_PERIOD_CODE[granularity]),
         "value": nums[mask].to_numpy()}
    )
    grouped = sub.groupby("period", sort=True)["value"].agg(aggfunc)
    labels = [_period_label(p, granularity) for p in grouped.index]
    values = [float(v) for v in grouped.to_numpy()]
    return labels, values, dropped


def to_long(df, time_col, value_cols, series_col, layout):
    """Normalize any supported layout to a tidy ``[time, series, value]`` frame.

    Row order is preserved. ``value`` is left uncoerced — numeric coercion
    happens downstream in ``clean_series`` / ``aggregate``.
    """
    if layout not in LAYOUTS:
        raise ValueError(f"Unknown layout {layout!r}; expected one of {LAYOUTS}.")

    value_cols = tuple(value_cols)
    needed = [time_col, *value_cols]
    if layout == "long":
        needed.append(series_col)
    missing = [c for c in needed if c is not None and c not in df.columns]
    if missing:
        raise ValueError(f"Column(s) not in the data: {missing}")

    if layout == "single":
        out = pd.DataFrame({
            "time": df[time_col].to_numpy(),
            "series": _ALL_SERIES,
            "value": df[value_cols[0]].to_numpy(),
        })
        return out

    if layout == "long":
        value_col = value_cols[0]
        if series_col is None or series_col in (time_col, value_col):
            raise ValueError(
                "Long layout needs a distinct series column."
            )
        return pd.DataFrame({
            "time": df[time_col].to_numpy(),
            "series": df[series_col].astype(str).to_numpy(),
            "value": df[value_col].to_numpy(),
        })

    # wide
    if not value_cols:
        raise ValueError("Wide layout needs at least one value column.")
    melted = df.melt(
        id_vars=[time_col],
        value_vars=list(value_cols),
        var_name="series",
        value_name="value",
    )
    return melted.rename(columns={time_col: "time"})[["time", "series", "value"]]


def series_names(long_df):
    """Distinct series names in first-appearance order."""
    seen = []
    for s in long_df["series"]:
        if s not in seen:
            seen.append(s)
    return seen


def collapse_series(long_df, view, combine_func="sum"):
    """Reduce a tidy long frame to a two-column ``[time, value]`` frame.

    ``view`` is either :data:`COMBINED_VIEW` (aggregate across series per time
    with ``combine_func``) or a series name (filter to it). Raises
    ``ValueError`` for an unknown series name.
    """
    if view == COMBINED_VIEW:
        nums = pd.to_numeric(long_df["value"], errors="coerce")
        sub = pd.DataFrame({"time": long_df["time"].to_numpy(), "value": nums})
        sub = sub.dropna(subset=["value"])  # drop non-numeric before grouping
        grouped = (
            sub.groupby("time", sort=False)["value"]
            .agg(combine_func)
            .reset_index()
        )
        return grouped.reset_index(drop=True)

    matched = long_df[long_df["series"] == view]
    if matched.empty:
        raise ValueError(f"No rows for series {view!r}.")
    return (
        matched[["time", "value"]]
        .reset_index(drop=True)
    )
