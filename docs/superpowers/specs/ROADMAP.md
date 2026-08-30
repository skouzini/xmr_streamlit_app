# XmR App — Feature Roadmap

Status of the app as of 2026-08-30. Written to hand off to a future session.

## Done (merged to `main`)

1. Sidebar layout + Charts/Data tabs (#2)
2. Mean/median centerlines — proper median XmR (#3)
3. Time-granularity aggregation — day/week/month/quarter/year (#4)
4. Multiple series — long/wide layouts, pick-one / combined views (#5)

## Planned — recommended order

Each has its own spec file in this directory. Do them one branch → one PR at
a time, TDD, following the same workflow as #2–#5 (see "Working style"
below).

| # | Feature | Spec | Size | Why this slot |
|---|---------|------|------|---------------|
| 5 | **Date filtering** (trim head/tail dates) | `2026-08-30-date-filtering-design.md` | S | Independent, tiny, immediately useful. Introduces the shared date-parsing helper the next three need. |
| 6 | **Baseline period** (limits from a chosen window, later points evaluated against them) | `2026-08-30-baseline-period-design.md` | S–M | `xmr.analyze()` already takes a `baseline` index range — mostly UI + a chart shaded region. Foundational for #7 and #8. |
| 7 | **Trended XmR** (sloped centerline, Wheeler's half-averages) | `2026-08-30-trended-xmr-design.md` | M | Explicitly "functions the same as the baseline feature" + a slope. Build on #6. |
| 8 | **Breakpoints** (segment the series, each segment its own limits, prior segments still drawn) | `2026-08-30-breakpoints-design.md` | L | The biggest — multi-segment analyze + overlay rendering. A segment ≈ a baseline-scoped analysis, so #6 should be solid first. |
| 9 | **Sidebar UX reorganization** | `2026-08-30-sidebar-ux-design.md` | S–M | Do last so it organizes the *final* set of controls (#5–#8 each add some). |

### Shared prerequisite (introduced by #5, reused by #6–#8)

A pure helper in `transform.py`:

```python
def parse_time(df, time_col):
    """Return a pandas datetime64 Series (NaT where a value doesn't parse),
    suppressing the 'could not infer format' UserWarning like aggregate() does.
    """
```

`aggregate()` already does this inline — factor it out in #5 and have
`aggregate` call it too.

## Working style (how #2–#5 were built)

- Branch per feature: `feature/<name>`, off fresh `main`.
- TDD: write the failing test first (`test_transform.py` for pure functions,
  `test_app.py` for figure/render/Inputs), implement, run the full suite.
- `xmr.py` = pure stats, no Streamlit. `transform.py` = pure data-shaping, no
  Streamlit. `app.py` = Streamlit UI only.
- `Inputs` (NamedTuple in `app.py`) carries every sidebar choice into
  `_render_charts_tab`. It has 14 fields today; #9 may restructure it.
- Verify in a browser via a throwaway `_smoke.py` that monkeypatches
  `st.file_uploader` to feed a fixture CSV, then `streamlit run _smoke.py
  --server.headless true --server.port <p>`; drive with the browser tools;
  delete the throwaway before committing.
- Push the branch, open a PR with `gh pr create`, let the user merge.
- Update `~/.claude/projects/-Users-jsk-Desktop-XmR-Streamlit-App/memory/`
  after each feature.

## Current key files

- `xmr.py` — `analyze(values, ruleset=1, baseline=None, x_center="mean",
  mr_center="mean") -> XmRResult`. `baseline` is a `(start, end)` half-open
  index pair. `XmRResult` fields: `values, moving_ranges, x_center, unpl,
  lnpl, mr_center, mr_upper, violations, x_zone_bounds, x_center_method,
  mr_center_method`.
- `transform.py` — `clean_series`, `aggregate`, `to_long`, `collapse_series`,
  `series_names`; constants `GRANULARITIES`, `AGGFUNCS`, `COMBINE_FUNCS`,
  `LAYOUTS`, `COMBINED_VIEW`.
- `app.py` — `Inputs`, `_sidebar_inputs`, `_render_charts_tab`,
  `_render_data_tab`, `_xmr_figure`, `_summary_caption`, `_ruleset_help`,
  `_signals_table_rows`, `SAMPLE_CSV`.
- `_render_charts_tab` pipeline today:
  `to_long → collapse_series (or passthrough) → clean_series|aggregate →
  analyze → _xmr_figure + signals table + summary caption`.
