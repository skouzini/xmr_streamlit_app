# XmR Chart Analyzer

A Streamlit app for analyzing time-series data with XmR (individuals and
moving-range) control charts, following Donald Wheeler's process-behaviour
chart method.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app opens on a bundled sample dataset. To analyze your own:

1. Upload a CSV or `.xlsx` file from the sidebar.
2. Pick the time/label column and the value column.
3. Choose a detection ruleset.

`sample_data.csv` (the bundled sample) is also in the repo — time column
`week`, value column `measurement`.

## What it computes

- Individual values (X) chart and moving-range (mR) chart
- Center lines: mean (default) or median of the values, and mean or median
  of the moving ranges — each chart's centerline is chosen independently
- X-chart limits: `center +/- k * mR-center`
- mR upper range limit: `k_url * mR-center` (no lower limit)

The scaling factors depend on whether the mR centerline is the mean or the
median moving range:

| mR centerline | X-limit factor `k` | mR upper-limit factor `k_url` |
|---------------|--------------------|-------------------------------|
| mean          | 2.660              | 3.268                         |
| median        | 3.145              | 3.865                         |

(Median XmR is the outlier-robust variant; the factors are Wheeler's.)

## Detection rules

| Rule | Signal |
|------|--------|
| 1 | A point outside the limits (3 sigma) |
| 2 | 8 consecutive points on one side of the center line |
| 3 | 3 of 4 consecutive points beyond 1.5 sigma, same side |
| 4 | 2 of 3 consecutive points beyond 2 sigma, same side |
| 5 | 4 of 5 consecutive points beyond 1 sigma, same side |

- **Ruleset 1:** rules 1, 2, 3
- **Ruleset 2:** rules 1, 2, 4, 5

The mR chart uses rule 1 only.

## Multiple series

A file can hold several series (e.g. budget line items). Pick a **Data
layout**:

- **Single** — one value column (the default).
- **Long** — one value column plus a column naming the series.
- **Wide** — one column per series (multiselect).

With Long or Wide you then choose a **View**: any single series' XmR chart,
or **Combined** — all series merged per date with a chooseable function
(**sum** for a budget total, mean, min, max, count). Time-granularity
aggregation and the centerline choice apply to whichever series results.

## Time-granularity aggregation

By default each row is one point ("Raw"). You can instead bucket the data by
**day / week / month / quarter / year** and pick an aggregation — **sum**
(e.g. a budget), **mean** (readings), median, min, max, count, first, or last.
Aggregation needs the time column to parse as dates; if it doesn't, the app
falls back to the raw series with a warning.

## Limits on small samples

- Fewer than 4 data points: no chart.
- Fewer than 17 moving ranges (~18 points): charts render, but the limits
  are flagged as soft / provisional.
- A sustained shift in the process inflates the limits computed over all the
  data (the moving ranges spanning the shift widen `mR-bar`), which is exactly
  what the not-yet-implemented baseline locking will address.

## Tests

```bash
pytest
```

## Not yet implemented

Baseline / limit locking (compute limits from a chosen subset, then plot
later points against fixed limits), in-app data editing, and export. The
`analyze()` function already accepts a `baseline` argument for the first of
these.
