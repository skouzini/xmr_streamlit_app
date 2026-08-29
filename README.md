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

1. Upload a CSV or `.xlsx` file.
2. Pick the time/label column and the value column.
3. Choose a detection ruleset.

Try `sample_data.csv` with time column `week` and value column
`measurement`.

## What it computes

- Individual values (X) chart and moving-range (mR) chart
- Center lines: mean of the values, mean of the moving ranges
- X-chart limits: `X-bar +/- 2.660 * mR-bar`
- mR upper range limit: `3.268 * mR-bar` (no lower limit)

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

## Limits on small samples

- Fewer than 4 data points: no chart.
- Fewer than 17 moving ranges (~18 points): charts render, but the limits
  are flagged as soft / provisional.

## Tests

```bash
pytest
```

## Not yet implemented

Baseline / limit locking (compute limits from a chosen subset, then plot
later points against fixed limits), in-app data editing, and export. The
`analyze()` function already accepts a `baseline` argument for the first of
these.
