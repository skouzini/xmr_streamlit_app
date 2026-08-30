# Date Filtering — Design

**Roadmap slot:** #5 (do first of the remaining five). **Size:** S.
**Status:** Planned — not started.

## Purpose

Let the user trim leading/trailing rows by date — e.g. drop a ramp-up period
at the start or an incomplete final month — without editing the file.

## Prerequisite this feature introduces

Factor date parsing out of `aggregate()` into a shared pure helper in
`transform.py`:

```python
def parse_time(series):
    """pd.to_datetime(series, errors='coerce') with the 'could not infer
    format' UserWarning suppressed. Returns a datetime64 Series (NaT where
    unparseable)."""
```

`aggregate()` then calls `parse_time(df[time_col])` instead of its inline
`with warnings.catch_warnings(): ...`. No behavior change; one covering test
that `aggregate` still passes.

## New pure function — `transform.py`

```python
def date_filter(df, time_col, start=None, end=None):
    """Return df restricted to rows whose parsed time is within
    [start, end] inclusive. start/end are date/Timestamp or None (open).
    Rows whose time doesn't parse are kept only when both bounds are None
    (i.e. filtering off); otherwise they are dropped.
    Order preserved; input not mutated.
    """
```

- Applied to the **raw uploaded frame**, before `to_long` — so it filters
  every series consistently.
- If `start` and `end` are both None → return `df` unchanged (fast path,
  and non-date time columns keep working exactly as today).

## `_render_charts_tab` flow

Insert as step 0:

```
0. df = date_filter(df, time_col, inp.date_start, inp.date_end)
1. long_df = to_long(df, ...)
...
```

If the filter leaves `< MIN_POINTS` rows, the existing guard fires with a
message that mentions the date range.

## Sidebar

Under the time-column picker, before "Data layout":

- A checkbox **"Filter by date range"** (default off).
- When on: two `st.date_input`s — **From** / **To** — defaulted to the min
  and max parsed dates in the file. If the time column has no parseable
  dates, show `st.caption("Time column isn't dates — date filter
  unavailable.")` and don't render the inputs.

`Inputs` gains `date_start: date | None`, `date_end: date | None`
(both None when the checkbox is off).

## Interaction with everything downstream

Date filter runs first, so aggregation, multi-series, baseline (#6), etc.
all operate on the trimmed frame. A pre-chart note when active:
`Dates: 2025-01-01 → 2025-12-31`.

## Data tab

Still shows the raw (unfiltered) upload. Add `· filtered to N rows` to the
caption when a filter is active.

## Tests (`test_transform.py`)

- `parse_time`: ISO dates parse; junk → NaT; no warning emitted
  (`pytest.warns(None)` / `recwarn`).
- `date_filter`: inclusive bounds; `start` only; `end` only; both None →
  identical object semantics (unchanged); unparseable rows dropped when
  filtering, kept when not; order preserved; input unmutated; multi-series
  long frame filtered on the shared date column.
- `aggregate` still green after the `parse_time` refactor.

`test_app.py`: `Inputs` round-trips the new fields; `_render_charts_tab` with
a date range draws the trimmed chart; the pre-chart note appears.
