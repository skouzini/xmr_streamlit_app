# XmR Streamlit App — Design

**Date:** 2026-08-29
**Status:** Approved for planning

## Purpose

A Streamlit app for analyzing time-series data with XmR (individuals and
moving-range) control charts, following Donald Wheeler's process-behaviour
chart methodology. This is the first iteration: upload data, build X and mR
charts, detect signals. Further functionality (baseline locking, annotations,
multiple charts, export) will be added later.

## Scope (this iteration)

In scope:

- CSV / Excel upload
- User selects the time/label column and the value column
- XmR calculation (moving ranges, center lines, limits) over all data
- Signal detection with two selectable rulesets
- Two stacked Plotly charts (X and mR) plus a signals table and a summary line

Explicitly deferred (design accommodates, UI does not expose yet):

- Baseline / limit locking (compute limits from a chosen subset, plot later
  points against fixed limits)
- Data entry / editing in-app
- Persistence, multi-dataset comparison, export/reporting

## Architecture

Two layers so the statistics are testable without Streamlit.

```
xmr_streamlit_app/
├── app.py              # Streamlit UI: upload, column pickers, charts, table
├── xmr.py              # pure functions: moving ranges, limits, rule detection
├── tests/
│   └── test_xmr.py     # pytest against xmr.py with hand-computed references
├── sample_data.csv     # small example file to try the app
├── requirements.txt    # streamlit, pandas, plotly, openpyxl, pytest
├── .gitignore          # python + streamlit
└── README.md
```

`xmr.py` receives an already-ordered sequence of numbers and returns a result
object. `app.py` does only I/O and rendering — it hands ordered values to
`xmr.py` and draws what comes back.

### Git

- `git init` in the project root
- remote `origin` = `https://github.com/skouzini/xmr_streamlit_app.git`
- Each feature is developed on its own feature branch off `main`.
- Commits and pushes to the feature branch happen freely as work progresses.
- When a feature is complete and verified, a pull request is opened to merge
  the feature branch into `main` — with explicit permission before opening
  each PR.
- `main` receives changes only through merged pull requests.

## XmR calculations (`xmr.py`)

Standard Wheeler XmR math.

- **Moving ranges:** `mR_i = |x_i - x_{i-1}|` for i = 2..n. Length n-1.
- **Center lines** (computed over the baseline; baseline defaults to all points):
  - `X̄` = mean of the individual values
  - `m̄R` = mean of the moving ranges
- **X chart limits:**
  - UNPL = `X̄ + 2.660 · m̄R`
  - LNPL = `X̄ - 2.660 · m̄R`
- **mR chart limits:**
  - upper range limit URL = `3.268 · m̄R`
  - no lower range limit
- **Sigma zones on the X chart** (multipliers on `m̄R`):
  - 1σ = 0.887
  - 1.5σ = 1.330
  - 2σ = 1.773
  - 3σ = 2.660 (the limits)

`2.660 = 3 / 1.128` (d2 for n=2); `3.268` is the D4 factor for n=2. The
intermediate multipliers are the 3σ multiplier scaled: `0.887 = 2.660/3`,
`1.330 = 2.660/2`, `1.773 = 2·2.660/3`.

### Detection rules

Zones are **nested**: "beyond 1.5σ" means anywhere past 1.5σ from the center
line, which includes points past 2σ and 3σ.

- **Rule 1** — a single point outside the limits (beyond 3σ).
- **Rule 2** — 8 consecutive points on the same side of the center line.
- **Rule 3** — 3 of 4 consecutive points, on the same side, beyond 1.5σ.
  The region between the limits spans 6σ (LNPL to UNPL); its upper (or lower)
  25% is the outermost 1.5σ, i.e. the zone from 1.5σ to the limit.
- **Rule 4** — 2 of 3 consecutive points, on the same side, beyond 2σ.
- **Rule 5** — 4 of 5 consecutive points, on the same side, beyond 1σ.

### Rulesets (selectable in the UI)

- **Ruleset 1:** rules 1, 2, 3
- **Ruleset 2:** rules 1, 2, 4, 5

### Which points get flagged

For the "k of m" rules (3, 4, 5): flag **only the qualifying points** — the
points that actually contribute to the signal, on the triggering side, beyond
the relevant zone. The non-qualifying points inside the window are not flagged.
A point can carry more than one rule marker (e.g. a point beyond 3σ that is
also part of a Rule 3 group carries both Rule 1 and Rule 3).

### mR chart

Rule 1 only — a moving range above the URL — regardless of the selected
ruleset. Rules 2–5 are not applied to the mR chart.

### API

- Each rule is its own function taking the value array, center line, and the
  relevant zone boundary(ies); it returns the set of violating indices.
- `analyze(values, ruleset, baseline=None)`:
  - `values`: ordered sequence of floats
  - `ruleset`: 1 or 2
  - `baseline`: optional slice / index range used to compute `X̄` and `m̄R`;
    default None means use all points
  - returns a result object (dataclass) with arrays: `values`,
    `moving_ranges`, scalars `x_center`, `unpl`, `lnpl`, `mr_center`,
    `mr_upper`, and `violations`: a list of `(index, rule_number, chart)`
    tuples where `chart` is `"x"` or `"mr"`.

## UI & data flow (`app.py`)

Single page, top to bottom:

1. **Upload** — `st.file_uploader` accepting `.csv`, `.xlsx`. Excel via
   `openpyxl`; if the workbook has multiple sheets, show a sheet picker.
2. **Column mapping** — two `st.selectbox`es: time/label column and value
   column. Show a preview of the raw table (`st.dataframe`).
3. **Options** — ruleset selector (Ruleset 1 / Ruleset 2). The value column is
   coerced to numeric; rows with non-numeric or missing values are dropped
   with a visible note (e.g. "skipped 3 rows"). Data is kept in file order —
   XmR is order-sensitive and file order is taken as process order.
4. **Charts** — two stacked Plotly figures sharing the x-axis:
   - **X chart:** individual values as line + markers; center line; UNPL and
     LNPL as horizontal lines; violating points colored red with hover text
     listing the rule number(s).
   - **mR chart:** moving ranges as line + markers; `m̄R` center line; URL
     line; points above URL colored red.
5. **Signals table** — `st.dataframe` listing every flagged point: time/label,
   value, rule number(s), chart.
6. **Summary line** — n points, `X̄`, `m̄R`, UNPL, LNPL, URL, total signal
   count.

Data flow:
`upload → DataFrame → (time, value) selection → cleaned ordered value array
→ xmr.analyze(values, ruleset) → result → Plotly figures + table`.

## Error handling

All surfaced as `st.warning` / `st.error` — never a raw traceback.

- No file uploaded yet → show instructions and point to `sample_data.csv`,
  then stop.
- File will not parse → error showing the parser's message.
- Fewer than 4 numeric values after cleaning → error: "XmR charts need at
  least 4 data points." No chart.
- Fewer than 17 moving ranges (i.e. fewer than 18 numeric data points) →
  render the charts, but show a warning that the limits are based on limited
  data and should be treated as **soft** (provisional) until roughly 18+
  points are available.
- All-identical values → `m̄R = 0`, limits collapse onto the mean; show a
  warning that the chart is degenerate, still render.
- Non-numeric time column is fine — it is only used for axis labels.

## Testing

`tests/test_xmr.py`, pytest, against `xmr.py`:

- Moving ranges from a known small series.
- `X̄`, `m̄R`, UNPL, LNPL, URL against hand-computed reference values.
- Each rule function in isolation: a crafted series that triggers exactly
  Rule 2, exactly Rule 3, exactly Rule 4, exactly Rule 5.
- Nested-zone case: a point beyond 3σ counts toward a Rule 3 group.
- "k of m" flags only the qualifying points (not the whole window).
- Ruleset 1 vs Ruleset 2 produce the expected different violation sets on the
  same series.
- Edge cases: constant series; exactly 4 points; a series with dropped rows;
  the <17 moving-range soft-limits boundary.

`app.py` is kept thin; covered by manual run against `sample_data.csv`. No
Streamlit UI tests in this iteration.

## Dependencies

`requirements.txt`: `streamlit`, `pandas`, `plotly`, `openpyxl`, `pytest`.
