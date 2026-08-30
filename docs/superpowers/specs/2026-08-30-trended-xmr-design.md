# Trended XmR (Sloped Centerline) — Design

**Roadmap slot:** #7. **Size:** M. **Status:** Planned — not started.
**Depends on:** #6 (baseline period) — this "functions the same as the
baseline feature" per the user, plus a slope.

## Purpose

For a process that is drifting at a roughly constant rate (e.g. spending
creeping up month over month), a flat centerline flags everything. A
*trended* XmR fits a sloped centerline and puts the usual limits around the
slope, so the question becomes "is it increasing *predictably*?"

## Wheeler's method (user has the source)

Given the baseline window of values `b[0..k-1]`:

1. Split the window in half: first half `b[:k//2]`, second half
   `b[k//2:]` (if `k` is odd, the middle point is dropped or assigned per
   Wheeler — **confirm from the user's source which; default: drop the
   middle point when odd**).
2. `y1 = mean(first half)` at the median index of the first half;
   `y2 = mean(second half)` at the median index of the second half.
3. Slope `m = (y2 - y1) / (idx2 - idx1)`; the centerline is the line through
   those two points, **extended across the whole series** (baseline and
   beyond).
4. Moving ranges and `mR̄` (or median mR) are computed **from the detrended
   baseline values** — i.e. subtract the fitted line first, then take
   `|Δ|`. `mR̄` (mean or median per the existing centerline toggle) →
   the usual `2.660` / `3.145` factor.
5. At each point `i`, `centerline(i) = y1 + m * (i - idx1)`;
   `UNPL(i) = centerline(i) + factor * mR̄`,
   `LNPL(i) = centerline(i) - factor * mR̄`. Limits are parallel sloped
   lines.
6. The mR chart is unchanged in shape — flat `mR̄` centerline, flat URL —
   because it is built on the detrended ranges.
7. Detection rules run against the **sloped** limits and a point's side
   relative to the **sloped** centerline.

## `xmr.py` changes

Add `trend: bool = False` to `analyze()`. When `True`:

- `baseline` is required (raise `ValueError` if `None`) — the trend is fit
  on the baseline window, same as the flat baseline feature.
- `XmRResult` gains `x_centerline: list[float]` (per-point centerline) and
  `unpl_line: list[float]` / `lnpl_line: list[float]` (per-point limits).
  For the non-trend case these are constant lists (fill with the existing
  scalars) so the figure code has one path.
- `x_center` / `unpl` / `lnpl` scalars stay for the summary caption — set
  them to the baseline-midpoint values (or keep as the flat-fit values;
  decide in implementation, document in the caption).
- Rule functions currently take scalar `center` / `lower` / `upper`. Extend
  them (or add trend-aware wrappers) to accept per-point arrays. `rule_1`,
  `rule_k_of_m` become "value vs per-point bound"; `rule_2` becomes "side of
  per-point centerline". Keep the flat path calling the array versions with
  constant arrays — no separate code path.

This is the real work of the feature: making the rule engine per-point
instead of scalar. Do it as its own commit with its own tests before
wiring the slope.

## `_xmr_figure`

- Replace the three `_labeled_hline` calls on the X chart with polylines
  when `result.x_centerline` is non-constant: add `go.Scatter` traces for
  the centerline / UNPL / LNPL using `result.*_line`, same gray palette and
  dash pattern, right-edge numeric annotation showing the *final* value.
- Flat case: detect constant lists and keep the current `add_hline` for a
  crisp horizontal rule (or just always use polylines — simpler, one path;
  verify it looks as clean).
- mR chart unchanged.
- Secondary zone lines (`x_zone_bounds`) also become sloped polylines.

## Sidebar

Extend the baseline section: a radio **"Centerline"** — `Flat` (default) /
`Trended (sloped)`. `Trended` is only enabled when a baseline period is set
(it depends on one). `Inputs` gains `trend: bool`.

## Notes

- Pre-chart note: `Trended centerline — slope +12.4 / period (fit on
  baseline)`.

## Tests

`test_xmr.py`:
- The per-point rule engine: constant arrays reproduce today's results
  exactly (regression — run the existing rule assertions through the array
  path).
- A crafted rising baseline: known `y1`, `y2`, slope; assert `x_centerline`,
  `unpl_line`, `lnpl_line` at several indices against hand computation.
- Odd-length baseline handling (per the confirmed Wheeler convention).
- `trend=True` without `baseline` → `ValueError`.
- Detrended moving ranges: a perfectly-linear baseline → `mR̄ ≈ 0` →
  degenerate but not an error.

`test_app.py`:
- `_xmr_figure` draws sloped centerline / limit traces (non-constant
  `x_centerline`) as `go.Scatter`, not `hline` shapes.
