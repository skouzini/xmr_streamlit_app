# Multiple Series — Design

**Date:** 2026-08-29
**Status:** Approved
**Feature:** 3 of 3 on the roadmap (after median centerlines and time-granularity aggregation).

## Purpose

Let a user analyze a file that contains several series (e.g. a budget with
multiple line items per date), and either view any single series' XmR chart
or a combined chart across all series.

## Scope

In scope:

- Three input layouts: **Single** (today's behavior), **Long** (a category
  column), **Wide** (multiple value columns).
- Two views once a layout with series is chosen: **pick one series**, or
  **Combined** (aggregate across series per date with a chooseable function,
  default Sum).
- Composes with the existing time-granularity aggregation and mean/median
  centerlines — those apply to the resulting single series.

Out of scope (possible later): overlay of multiple series on one chart,
small-multiples (one chart per series), per-series limit comparison.

## Structural change: new `transform.py` module

`app.py` has grown past ~470 lines and this feature adds ~3 more pure
data-shaping functions. Move the pure, Streamlit-free functions into a new
`transform.py`:

- `clean_series` (moved from `app.py`)
- `aggregate` + `_period_label` + the `_GRANULARITIES` / `_PERIOD_CODE` /
  `_AGGFUNCS` constants (moved from `app.py`)
- `to_long` (new)
- `collapse_series` (new)

`app.py` imports what it needs from `transform`. Tests split: the pure
functions get `tests/test_transform.py`; `tests/test_app.py` keeps the
figure/inputs/rendering tests. `xmr.py` is untouched.

## Data model

Everything normalizes to a tidy long DataFrame with columns
`time`, `series`, `value` before any charting.

### `to_long(df, time_col, value_cols, series_col, layout) -> DataFrame`

Returns a DataFrame with exactly the columns `time`, `series`, `value`
(in that order), preserving row order.

- `layout == "single"`: `value_cols` has one entry; `series_col` is None.
  Output `series` is the constant string `"(all)"`.
- `layout == "long"`: `value_cols` has one entry; `series_col` names the
  category column. Output is `df[[time_col, series_col, value_col]]` renamed;
  `series` values are `df[series_col]` cast to `str`.
- `layout == "wide"`: `value_cols` has one or more entries;
  `series_col` is None. Output is `pd.melt(df, id_vars=[time_col],
  value_vars=list(value_cols), var_name="series", value_name="value")` with
  `time_col` renamed to `time`; `series` values are the column names.

Raises `ValueError` if:
- `layout == "long"` and `series_col` is None, equals `time_col`, or equals
  the value column.
- `layout == "wide"` and `value_cols` is empty.
- any named column is missing from `df`.

`value` is left as-is here (not coerced); numeric coercion happens later in
`clean_series` / `aggregate`, consistent with today.

### `collapse_series(long_df, view, combine_func) -> DataFrame`

Takes a tidy long frame and returns a two-column `DataFrame[time, value]`
(one row per original `(time, series)` row for a single series; one row per
`time` for Combined), ready for `clean_series` / `aggregate`.

- `view == "Combined"`: `long_df.groupby("time", sort=False)["value"]
  .agg(combine_func)` back to a `[time, value]` frame. `combine_func` is one
  of `sum`, `mean`, `min`, `max`, `count` (default `sum`). Non-numeric
  values coerce to NaN and are excluded from the aggregate (mirroring
  `clean_series`); a `time` whose values are all non-numeric produces NaN
  and is dropped.
- `view == "<series name>"`: `long_df[long_df["series"] == view]` reduced to
  `[time, value]`. Raises `ValueError` if no rows match.

Order: the frame keeps first-appearance order of `time`.

## `_render_charts_tab` flow (updated)

```
1. long_df = to_long(df, time_col, value_cols, series_col, layout)
2. series_df = collapse_series(long_df, view, combine_func)   # -> [time, value]
3. if granularity == "raw":
       labels, values, dropped = clean_series(series_df, "time", "value")
   else:
       labels, values, dropped = aggregate(series_df, "time", "value",
                                           granularity, aggfunc)
4. analyze(values, ruleset, x_center, mr_center) -> figure + table + caption
```

Steps 1–2 are new. `to_long` / `collapse_series` `ValueError`s are caught and
shown with `st.error` + `return` (same pattern as the existing column-choice
errors), so the Data tab stays usable.

For `layout == "single"` the two new steps are near-passthroughs and behavior
is byte-for-byte what it is today.

## Sidebar (cascading)

Under the existing time/value column pickers:

1. **Data layout** — `st.radio`: Single (default) / Long / Wide.
2. If **Long**: **Series column** — `st.selectbox` over columns excluding the
   time and value columns.
   If **Wide**: **Value columns** — `st.multiselect` over columns excluding
   the time column (this replaces the single value-column pick for wide;
   default = the first non-time column).
3. If Long or Wide: **View** — `st.selectbox` with `"Combined"` first, then
   the sorted distinct series names.
4. If **View == "Combined"**: **Combine series by** — `st.selectbox`:
   Sum (default) / Mean / Min / Max / Count.

The existing "Aggregate by" / "Aggregation" / centerline / ruleset controls
stay where they are, below these.

### `Inputs` additions

`layout: str`, `series_col: str | None`, `value_cols: tuple[str, ...]`,
`view: str`, `combine_func: str`. For Single/Long, `value_cols` is a
one-tuple of the value-column pick; for Wide it is the multiselect result.

## Labels and notes

- Summary caption gains a leading segment: `Series: Groceries  |  n = …` or
  `Combined (sum of 4 series)  |  n = …`.
- Data tab caption gains `· N series` when a series column / wide layout is
  active.

## Error / edge handling

- Wide layout, nothing selected → `st.error`, `return`.
- Long layout, series column collides with time/value → `st.error`, `return`.
- A chosen single series with `< MIN_POINTS` points after the pipeline → the
  existing guard fires; message names the series.
- Combined with exactly one series → identical to viewing that series.
- `to_long` / `collapse_series` never mutate the input DataFrame.

## Testing

`tests/test_transform.py` (new; also covers the moved `clean_series` /
`aggregate` tests):

- `to_long`: single → one `"(all)"` series; long → correct rename and `str`
  series values; wide → melt with column names as series, row order; each
  `ValueError` path.
- `collapse_series`: pick-one filters correctly and preserves time order;
  Combined with sum / mean / count against hand-computed values; non-numeric
  values excluded; unknown series name raises; input not mutated.
- End-to-end on a small long budget frame: `to_long` → `collapse_series`
  (Combined, sum) → `aggregate` (month, sum) → expected labels/values.

`tests/test_app.py`:

- `Inputs` round-trips the new fields.
- `_render_charts_tab` with a wide `_inputs(...)` draws exactly one chart for
  a picked series and for Combined.
- `_render_charts_tab` shows an error and draws nothing for empty wide
  selection / colliding long series column.
- Summary caption includes the `Series:` / `Combined` segment.

## Migration / compatibility

Default layout is Single, so an existing session or the bundled sample
behaves exactly as before. No changes to `xmr.py`, `analyze()`, or the
`XmRResult` shape.
