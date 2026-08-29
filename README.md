# XmR Chart Analyzer

A Streamlit app for analyzing time-series data with XmR (individuals and
moving-range) control charts.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Upload `sample_data.csv` to try it: pick `week` as the time column and
`measurement` as the value column.

## Tests

```bash
pytest
```
