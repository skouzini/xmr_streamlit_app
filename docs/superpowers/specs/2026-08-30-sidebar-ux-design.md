# Sidebar UX Reorganization — Design

**Roadmap slot:** #9 (last — organizes the final control set).
**Size:** S–M. **Status:** Planned — not started.

## Problem

`_sidebar_inputs` renders a flat vertical stack of ~10 controls today, and
features #5–#8 add ~8 more (date filter, baseline, trend, breakpoints). It
becomes an unnavigable wall.

## Goal

Group the controls into labelled, collapsible sections in a sensible order,
so a first-time user sees only what they need and power features are tucked
away until wanted.

## Proposed structure (`st.sidebar` with `st.expander` / `st.subheader`)

1. **Data** (always open)
   - File uploader
   - Time column
   - Data layout → (Series column / Value columns) → View → Combine by
2. **Shape the series** (expander, open when any is non-default)
   - Filter by date range (#5)
   - Aggregate by / Aggregation (#3)
3. **Limits** (expander)
   - Detection ruleset (+ its tooltip)
   - X / mR chart centerline (mean/median) (#2)
   - Baseline period (#6) → Centerline: flat / trended (#7)
   - Breakpoints (#8)

Exact grouping is negotiable — the point is 3–4 sections, "Data" first and
open, advanced stuff behind expanders.

## Implementation notes

- `st.expander` inside `st.sidebar` works and persists open/closed state per
  rerun via `st.session_state` if you give each a `key`.
- Keep `_sidebar_inputs` returning the same `Inputs` NamedTuple — this is
  pure rearrangement of `st.*` calls plus expander wrappers. **No logic
  change**, so the existing `Inputs` round-trip test is the safety net.
- Consider splitting `_sidebar_inputs` into `_data_section(...)`,
  `_shape_section(...)`, `_limits_section(...)` helpers that each take the
  `df`/`columns` and return their slice of the inputs — keeps the function
  readable and testable.
- If `Inputs` has grown unwieldy (18+ fields by now), this is the moment to
  group it: nested NamedTuples (`inp.data.time_col`, `inp.limits.ruleset`)
  or a small dataclass per section. Update `_render_charts_tab` /
  `_render_data_tab` accordingly. Decide based on how bad it actually is.

## Tests

- The `Inputs` round-trip / default test still passes unchanged.
- If `_sidebar_inputs` is split, add a light test per section helper that it
  returns the expected keys with defaults given a minimal df (monkeypatch
  the `st.*` widgets to return their defaults).
- No new figure/analysis tests — this feature changes no output.

## Definition of done

- Every existing control still reachable and functional.
- Sidebar opens showing only the Data section expanded.
- A screenshot review with the user before merge (UX-only feature).
