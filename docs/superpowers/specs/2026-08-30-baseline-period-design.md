# Baseline Period — Design

**Roadmap slot:** #6. **Size:** S–M. **Status:** Planned — not started.
**Depends on:** #5 (`parse_time` helper).

## Purpose

Compute the XmR centerline and limits from a chosen historical window (the
"baseline"), then plot *all* points — including ones after the baseline —
against those fixed limits. Example: define the chart from 2024, then watch
2025 and 2026 against 2024's limits. Points outside the baseline never
affect `X̄` / `mR̄` / the limits.

## What already exists

`xmr.analyze(values, ruleset, baseline=None, ...)` already accepts
`baseline=(start, end)` — a half-open **index** range — and computes
`x_center` / `mr_center` from `values[start:end]` while running the rules
over the whole series. It is covered by `test_baseline_changes_limits` and
`test_baseline_too_short_raises`. **The stats are done.** This feature is
almost entirely UI + translating a date range to an index range + drawing
the baseline region.

Minor `xmr.py` gap to close first: `analyze` only checks `b_end - b_start
>= 2`. Add `if not (0 <= b_start < b_end <= n): raise ValueError` (a
deferred minor from the original build — see the original SDD ledger).

## Translating dates → indices

After the pipeline produces `labels` (the x-axis strings) and `values`, the
baseline is expressed by the user as a date range. Convert:

```python
def baseline_index_range(labels, start, end):
    """labels are period strings ('2024-01', '2024-Q1', '2024', a date...).
    Parse each, return (i0, i1) half-open covering labels within [start, end].
    Raises ValueError if the window has < MIN_POINTS points."""
```

Put this in `transform.py` (pure, testable). It must handle every label
format `_period_label` can emit (`YYYY`, `YYYY-Qn`, `YYYY-MM`,
`YYYY-MM-DD`) plus raw passthrough labels — reuse `parse_time` with a
`YYYY-Qn` special case.

## `_render_charts_tab` flow

After `labels, values` are known and before `analyze`:

```
if inp.baseline_on:
    b = baseline_index_range(labels, inp.baseline_start, inp.baseline_end)
    result = analyze(values, ruleset=..., baseline=b, x_center=..., mr_center=...)
else:
    result = analyze(values, ...)          # unchanged
```

Errors (`< MIN_POINTS` in the window, window outside the data) → `st.error`
+ `return`.

## Chart — show the baseline region

In `_xmr_figure`, add an optional `baseline_span=(i0, i1)` param. When set,
draw a faint shaded `vrect` (`fig.add_vrect`) behind both subplots covering
categories `labels[i0]`..`labels[i1-1]`, with an annotation "baseline". Use
a very low-alpha fill from the existing gray palette so it doesn't fight the
data. Points before/after the baseline still render identically — the limit
lines simply extend across the whole width.

## Sidebar

New section after the aggregation controls:

- Checkbox **"Use a baseline period"** (default off).
- When on: **Baseline from** / **Baseline to** `st.date_input`s (defaults:
  the first ~⅓ of the data's date span, or first vs. last date). If the time
  column isn't dates, offer instead two number inputs "first N points" /
  "through point M" — or just "first N points" for v1. Keep it simple:
  **v1 = date inputs when the column parses as dates, otherwise a single
  "Baseline = first N points" number input.**

`Inputs` gains `baseline_on: bool`, `baseline_start`, `baseline_end` (dates
or the N-points int).

## Notes & summary

- Pre-chart note: `Baseline: 2024-01 → 2024-12 (12 points)`.
- Summary caption unchanged in shape; the numbers already reflect the
  baseline because `analyze` computed them from it.

## Tests

`test_transform.py`:
- `baseline_index_range` for each label format; window that starts/ends
  mid-series; `< MIN_POINTS` → `ValueError`; window entirely outside → error.

`test_xmr.py`:
- the new bounds `ValueError` (`baseline=(-1, 5)`, `baseline=(2, 2)`,
  `baseline=(0, 999)`).
- a full case: 10 stable points + 3 shifted; `baseline=(0, 10)`; assert the
  shifted points are flagged by rule 1 while the limits equal the
  stable-window limits.

`test_app.py`:
- `_xmr_figure` with `baseline_span` adds exactly one `vrect` shape spanning
  the right categories.
- `_render_charts_tab` with `baseline_on` passes the right index range to
  `analyze` (monkeypatch `analyze`, assert the `baseline` kwarg).
