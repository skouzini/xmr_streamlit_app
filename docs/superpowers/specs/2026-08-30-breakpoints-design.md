# Breakpoints (Segmented XmR) — Design

**Roadmap slot:** #8 (the largest). **Size:** L.
**Status:** Planned — not started. **Depends on:** #6 solid; benefits from
#7's per-point rule engine.

## Purpose

Let the user mark one or more breakpoints in time. Each segment between
breakpoints gets its **own** XmR limits (its own `X̄`, `mR̄`, UNPL/LNPL).
All segments are drawn on one chart, and the **previous segments' limit
lines stay visible** so you can see how the process shifted. Example:
Jan–Jun is one XmR, Jul–Dec is a second, both shown together.

## Model

- A breakpoint is a position in the series (best expressed as a date, mapped
  to a boundary index like the baseline feature does).
- `k` breakpoints → `k + 1` segments. Segment `s` spans
  `[bounds[s], bounds[s+1])`.
- Each segment is analyzed **independently**: run `analyze` on that slice
  (its own `baseline = whole segment`). Detection rules run **within** the
  segment only — a run of 8 doesn't carry across a breakpoint.
- Optionally, a segment can itself use the baseline / trend features (a
  segment's limits fit on the first part of the segment). **v1: keep it
  simple — each segment's limits are computed from the entire segment,
  flat.** Baseline/trend *per segment* is a later refinement.

## `xmr.py` / new module

Add a thin orchestrator — probably in `xmr.py`:

```python
def analyze_segments(values, breakpoints, ruleset=1, x_center="mean",
                     mr_center="mean") -> list[SegmentResult]
```

where `breakpoints` is a sorted list of boundary indices and each
`SegmentResult` carries: the segment's index span, its `XmRResult`, and the
absolute point indices so the figure can place things. Each segment must
have `>= MIN_POINTS` points or it is reported as a skipped/short segment
(surface in the UI, don't crash).

`analyze_segments` with an empty `breakpoints` list must equal today's
single `analyze` (one segment = whole series) — regression anchor.

## `transform.py`

```python
def breakpoint_indices(labels, break_dates) -> list[int]
```

Reuse `baseline_index_range`'s label-parsing. Each break date → the index of
the first point on/after that date. Dedupe, sort, drop 0 and n.

## `_xmr_figure`

Biggest change. Instead of one set of limit lines spanning the width:

- For each segment, draw its centerline / UNPL / LNPL / zone lines as short
  polylines (or `hline` with `x0`/`x1` bounded to the segment's category
  range) in the standard gray, **plus** a thin vertical divider at each
  breakpoint.
- "Previous segments visible" is automatic — every segment's lines are on
  the figure. Consider slightly fading older segments, or a distinct dash
  per segment, or a per-segment legend entry. **v1: same style for all,
  divider lines + the segment's own right-edge value labels.** Get the user
  to react to a screenshot.
- The data trace is still one continuous line across all points; the mR
  chart likewise, but with `connectgaps=False` at breakpoints (insert a
  `None` at each boundary so the mR line breaks) — the moving range that
  spans a breakpoint is not meaningful.
- Signals: aggregate all segments' violations, offset to absolute indices.

## Sidebar

New "Breakpoints" section:

- `st.multiselect` or repeated `st.date_input`s to add break dates
  (multiselect over the distinct period labels is simplest — the user picks
  which labels start a new segment).
- `Inputs` gains `breakpoints: tuple[str, ...]` (the chosen labels/dates).

## `_render_charts_tab`

```
labels, values = ...                       # after series + granularity
breaks = breakpoint_indices(labels, inp.breakpoints)
if not breaks:
    result = analyze(...)                   # unchanged single path
    _xmr_figure(labels, result, ...)
else:
    segments = analyze_segments(values, breaks, ...)
    _xmr_figure_segmented(labels, segments, ...)   # or one figure fn, branch inside
```

Signals table and summary caption need a per-segment breakdown
(`Segment 1 (Jan–Jun): X̄ = …` / `Segment 2 (Jul–Dec): X̄ = …`).

## Tests

`test_xmr.py`:
- `analyze_segments([...], [])` == a list of one whose `XmRResult` equals
  `analyze([...])`.
- Two segments with clearly different means → each `SegmentResult` has its
  own limits; a run of 8 straddling the breakpoint is NOT flagged.
- A segment with `< MIN_POINTS` → reported short, others still analyzed.

`test_transform.py`:
- `breakpoint_indices` maps dates to boundary indices; dedupe/sort; ignores
  0 and n.

`test_app.py`:
- segmented `_xmr_figure` draws `k+1` sets of limit lines and `k` dividers;
  mR line has a gap at each breakpoint.

## Open questions for the implementing session

- Visual treatment of "previous segments" — same style vs faded vs
  per-segment color. Decide with a screenshot.
- Whether a segment may carry its own baseline/trend (defer to v2 unless the
  user wants it now).
