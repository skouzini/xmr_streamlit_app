# XmR Charts v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit app that turns an uploaded CSV/Excel time series into XmR (individuals + moving-range) control charts with signal detection.

**Architecture:** Pure statistics live in `xmr.py` (no Streamlit import) and are exercised by pytest against hand-computed reference values. `app.py` does only file I/O, column selection, and Plotly rendering, calling `xmr.analyze()`. One small pure helper in `app.py` (`clean_series`) is also unit-tested.

**Tech Stack:** Python 3.13, Streamlit, pandas, Plotly (`plotly.graph_objects`), openpyxl (Excel), pytest.

**Spec:** `docs/superpowers/specs/2026-08-29-xmr-streamlit-app-design.md`

## Global Constraints

- Dependencies limited to: `streamlit`, `pandas`, `plotly`, `openpyxl`, `pytest`. No others.
- `xmr.py` must not import `streamlit`.
- XmR scaling constants (verbatim): X-chart limit multiplier `2.660`; mR upper-limit multiplier `3.268`. Sigma-zone half-widths are derived: `k_sigma / 3 * 2.660 * mR_bar`.
- `MIN_POINTS = 4` — fewer numeric values than this is a `ValueError` from `analyze()` / an `st.error` in the UI, no chart.
- `SOFT_LIMIT_MIN_MR = 17` — fewer than this many moving ranges renders charts but shows a "soft / provisional limits" warning.
- Rulesets: `RULESETS = {1: (1, 2, 3), 2: (1, 2, 4, 5)}`.
- Data is kept in uploaded file order. Never sort it.
- "k of m" rules (3, 4, 5) flag only the qualifying points, not the whole window.
- The mR chart applies Rule 1 only (moving range above the upper range limit), regardless of ruleset.
- No raw tracebacks in the UI — every failure path is `st.error` / `st.warning` then `st.stop()`.
- Git: all work on branch `feature/xmr-charts-v1`. Commit and push to that branch freely. Opening a PR into `main` requires explicit user permission.

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `sample_data.csv`
- Create: `README.md`
- Create: `tests/__init__.py` (empty)

**Interfaces:**
- Consumes: nothing
- Produces: an installable environment and a sample data file later tasks and the README reference by name (`sample_data.csv`).

- [ ] **Step 1: Create the feature branch**

```bash
git checkout -b feature/xmr-charts-v1
```

- [ ] **Step 2: Write `requirements.txt`**

```
streamlit
pandas
plotly
openpyxl
pytest
```

- [ ] **Step 3: Write `.gitignore`** (it may already exist from workspace setup; ensure it contains exactly this)

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.DS_Store
.streamlit/secrets.toml
.superpowers/
```

- [ ] **Step 4: Write `sample_data.csv`**

```
week,measurement
2026-01-05,98
2026-01-12,102
2026-01-19,100
2026-01-26,97
2026-02-02,103
2026-02-09,99
2026-02-16,101
2026-02-23,100
2026-03-02,98
2026-03-09,102
2026-03-16,101
2026-03-23,99
2026-03-30,100
2026-04-06,103
2026-04-13,97
2026-04-20,101
2026-04-27,113
2026-05-04,115
2026-05-11,114
2026-05-18,116
2026-05-25,113
2026-06-01,117
2026-06-08,115
2026-06-15,114
```

- [ ] **Step 5: Write a minimal `README.md`**

```markdown
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
```

- [ ] **Step 6: Create the empty test package marker**

Create `tests/__init__.py` with no content.

- [ ] **Step 7: Verify the environment installs**

Run: `pip install -r requirements.txt`
Expected: completes without error; `python -c "import streamlit, pandas, plotly, openpyxl, pytest"` prints nothing and exits 0.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .gitignore sample_data.csv README.md tests/__init__.py
git commit -m "chore: project scaffold for XmR charts"
```

---

### Task 2: Core XmR statistics (`xmr.py`)

**Files:**
- Create: `xmr.py`
- Test: `tests/test_xmr.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - Module constants: `MIN_POINTS = 4`, `SOFT_LIMIT_MIN_MR = 17`, `X_LIMIT_SIGMA_MULT = 2.660`, `MR_UPPER_MULT = 3.268`, `RULESETS = {1: (1, 2, 3), 2: (1, 2, 4, 5)}`
  - `@dataclass XmRResult` with fields, in order: `values: list[float]`, `moving_ranges: list[float | None]` (length n, index 0 is `None`), `x_center: float`, `unpl: float`, `lnpl: float`, `mr_center: float`, `mr_upper: float`, `violations: list[tuple[int, int, str]]`
  - `analyze(values, ruleset=1, baseline=None) -> XmRResult` — this task returns a result whose `violations` is always `[]` (rules are added in Task 4). `baseline` is `None` or a `(start, end)` half-open index pair over `values`.
  - `_sigma_half_width(k_sigma, mr_center) -> float` — private helper `k_sigma / 3 * X_LIMIT_SIGMA_MULT * mr_center`. Not used within this task; Task 4 consumes it. It is a deliberate forward-looking helper, not dead code.

- [ ] **Step 1: Write the failing test**

Create `tests/test_xmr.py`:

```python
import pytest

from xmr import (
    MIN_POINTS,
    SOFT_LIMIT_MIN_MR,
    RULESETS,
    XmRResult,
    analyze,
)

SERIES_A = [10, 12, 11, 13, 10, 14, 12, 11]  # n=8, mR mean = 15/7


def test_constants():
    assert MIN_POINTS == 4
    assert SOFT_LIMIT_MIN_MR == 17
    assert RULESETS == {1: (1, 2, 3), 2: (1, 2, 4, 5)}


def test_moving_ranges_alignment():
    r = analyze(SERIES_A)
    assert isinstance(r, XmRResult)
    assert r.moving_ranges[0] is None
    assert r.moving_ranges[1:] == [2, 1, 2, 3, 4, 2, 1]
    assert len(r.moving_ranges) == len(SERIES_A)


def test_centers_and_limits():
    r = analyze(SERIES_A)
    assert r.x_center == pytest.approx(11.625)
    assert r.mr_center == pytest.approx(15 / 7)
    assert r.unpl == pytest.approx(11.625 + 5.7)
    assert r.lnpl == pytest.approx(11.625 - 5.7)
    assert r.mr_upper == pytest.approx(3.268 * 15 / 7)


def test_constant_series_is_degenerate_not_an_error():
    r = analyze([5, 5, 5, 5, 5])
    assert r.mr_center == 0
    assert r.x_center == r.unpl == r.lnpl == 5
    assert r.mr_upper == 0
    assert r.violations == []


def test_exactly_four_points_is_allowed():
    r = analyze([1, 2, 3, 4])
    assert len(r.moving_ranges) == 4
    assert r.moving_ranges[0] is None


def test_too_few_points_raises():
    with pytest.raises(ValueError):
        analyze([1, 2, 3])


def test_unknown_ruleset_raises():
    with pytest.raises(ValueError):
        analyze(SERIES_A, ruleset=99)


def test_baseline_changes_limits():
    base = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11]
    full = base + [20]
    r_base = analyze(full, baseline=(0, 10))
    r_all = analyze(full)
    assert r_base.x_center == pytest.approx(10.5)
    assert r_all.x_center == pytest.approx(125 / 11)
    assert r_base.unpl != pytest.approx(r_all.unpl)


def test_baseline_too_short_raises():
    with pytest.raises(ValueError):
        analyze(SERIES_A, baseline=(3, 4))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_xmr.py -v`
Expected: FAIL — `ImportError` / `ModuleNotFoundError: No module named 'xmr'`.

- [ ] **Step 3: Write `xmr.py`**

```python
"""Pure XmR (individuals + moving range) control-chart statistics.

No Streamlit import here — this module is unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_POINTS = 4
SOFT_LIMIT_MIN_MR = 17
X_LIMIT_SIGMA_MULT = 2.660  # 3-sigma multiplier on mR-bar for the X chart
MR_UPPER_MULT = 3.268       # upper-range-limit multiplier on mR-bar
RULESETS = {1: (1, 2, 3), 2: (1, 2, 4, 5)}


@dataclass
class XmRResult:
    values: list[float]
    moving_ranges: list[float | None]
    x_center: float
    unpl: float
    lnpl: float
    mr_center: float
    mr_upper: float
    violations: list[tuple[int, int, str]]


def _sigma_half_width(k_sigma: float, mr_center: float) -> float:
    """Half-width of the k-sigma zone on the X chart."""
    return k_sigma / 3.0 * X_LIMIT_SIGMA_MULT * mr_center


def analyze(values, ruleset: int = 1, baseline=None) -> XmRResult:
    values = [float(v) for v in values]
    n = len(values)
    if n < MIN_POINTS:
        raise ValueError(
            f"XmR charts need at least {MIN_POINTS} data points; got {n}."
        )
    if ruleset not in RULESETS:
        raise ValueError(
            f"Unknown ruleset {ruleset!r}; expected one of {sorted(RULESETS)}."
        )

    moving_ranges: list[float | None] = [None] + [
        abs(values[i] - values[i - 1]) for i in range(1, n)
    ]

    if baseline is None:
        b_start, b_end = 0, n
    else:
        b_start, b_end = baseline
    if b_end - b_start < 2:
        raise ValueError("baseline must span at least 2 points.")

    base_values = values[b_start:b_end]
    base_mr = [
        abs(base_values[i] - base_values[i - 1])
        for i in range(1, len(base_values))
    ]
    x_center = sum(base_values) / len(base_values)
    mr_center = sum(base_mr) / len(base_mr)

    unpl = x_center + X_LIMIT_SIGMA_MULT * mr_center
    lnpl = x_center - X_LIMIT_SIGMA_MULT * mr_center
    mr_upper = MR_UPPER_MULT * mr_center

    violations: list[tuple[int, int, str]] = []  # rules wired in Task 4

    return XmRResult(
        values=values,
        moving_ranges=moving_ranges,
        x_center=x_center,
        unpl=unpl,
        lnpl=lnpl,
        mr_center=mr_center,
        mr_upper=mr_upper,
        violations=violations,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_xmr.py -v`
Expected: PASS — all 9 tests green.

- [ ] **Step 5: Commit**

```bash
git add xmr.py tests/test_xmr.py
git commit -m "feat: XmR moving ranges, center lines, and control limits"
```

---

### Task 3: Signal-detection rule functions (`xmr.py`)

**Files:**
- Modify: `xmr.py` (add three functions)
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: nothing from other tasks
- Produces:
  - `rule_1(values, lower, upper) -> set[int]` — indices where `value > upper or value < lower`
  - `rule_2(values, center, run_length=8) -> set[int]` — indices belonging to any run of `run_length` or more consecutive points strictly on the same side of `center`; a point equal to `center` breaks the run and is never flagged. All points in a qualifying run are flagged, including as the run extends past `run_length`.
  - `rule_k_of_m(values, upper, lower, k, m) -> set[int]` — slides a window of `m` consecutive indices; within a window, if at least `k` points satisfy `value > upper` those points are flagged, and independently if at least `k` satisfy `value < lower` those are flagged. Upper and lower counts never combine. Returns empty when `len(values) < m`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_rules.py`:

```python
from xmr import rule_1, rule_2, rule_k_of_m


def test_rule_1_outside_limits():
    assert rule_1([0, 10, -10, 1], lower=-2, upper=3) == {1, 2}
    assert rule_1([1, 2, 1], lower=-5, upper=5) == set()
    # a point exactly on a limit is not outside
    assert rule_1([3, -2], lower=-2, upper=3) == set()


def test_rule_2_runs():
    assert rule_2([1] * 8, center=0) == set(range(8))
    assert rule_2([-1] * 8, center=0) == set(range(8))
    assert rule_2([1] * 10, center=0) == set(range(10))
    assert rule_2([1] * 7, center=0) == set()
    # a zero (on the center line) breaks the run
    assert rule_2([1, 1, 1, 1, 0, -1, 1, 1, 1, 1, 1, 1, 1, 1], center=0) == set(
        range(6, 14)
    )


def test_rule_k_of_m_three_of_four():
    # k=3, m=4, zone at +/-1.5
    assert rule_k_of_m([2, 2, 0, 2], upper=1.5, lower=-1.5, k=3, m=4) == {0, 1, 3}
    # 4th point inside the zone is not flagged
    assert rule_k_of_m([2, 2, 2, 0.5], upper=1.5, lower=-1.5, k=3, m=4) == {0, 1, 2}
    # nested zones: a point far past the limit still counts toward "beyond 1.5"
    assert rule_k_of_m([9, 2, 2, 0], upper=1.5, lower=-1.5, k=3, m=4) == {0, 1, 2}
    # lower side
    assert rule_k_of_m([-2, -2, 0, -2], upper=1.5, lower=-1.5, k=3, m=4) == {0, 1, 3}
    # only two on a side -> nothing
    assert rule_k_of_m([2, 0, 2, 0], upper=1.5, lower=-1.5, k=3, m=4) == set()
    # opposite sides never combine
    assert rule_k_of_m([2, -2, 2, -2], upper=1.5, lower=-1.5, k=3, m=4) == set()
    # window shorter than m
    assert rule_k_of_m([2, 2], upper=1.5, lower=-1.5, k=3, m=4) == set()


def test_rule_k_of_m_two_of_three():
    assert rule_k_of_m([2, 2, 0], upper=1.773, lower=-1.773, k=2, m=3) == {0, 1}
    assert rule_k_of_m([2, 0, 2], upper=1.773, lower=-1.773, k=2, m=3) == {0, 2}
    assert rule_k_of_m([2, 0, 0], upper=1.773, lower=-1.773, k=2, m=3) == set()


def test_rule_k_of_m_four_of_five():
    assert rule_k_of_m([1, 1, 1, 1, 0], upper=0.887, lower=-0.887, k=4, m=5) == {
        0,
        1,
        2,
        3,
    }
    assert rule_k_of_m([1, 1, 1, 0, 1], upper=0.887, lower=-0.887, k=4, m=5) == {
        0,
        1,
        2,
        4,
    }
    assert rule_k_of_m([1, 1, 1, 0, 0], upper=0.887, lower=-0.887, k=4, m=5) == set()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL — `ImportError: cannot import name 'rule_1' from 'xmr'`.

- [ ] **Step 3: Add the rule functions to `xmr.py`**

Insert these above `analyze()` (after `_sigma_half_width`):

```python
def rule_1(values, lower: float, upper: float) -> set[int]:
    """Points outside the control limits."""
    return {i for i, v in enumerate(values) if v > upper or v < lower}


def rule_2(values, center: float, run_length: int = 8) -> set[int]:
    """Runs of `run_length`+ consecutive points on one side of the center."""
    flagged: set[int] = set()
    run: list[int] = []
    last_sign = 0
    for i, v in enumerate(values):
        sign = 1 if v > center else (-1 if v < center else 0)
        if sign != 0 and sign == last_sign:
            run.append(i)
        else:
            run = [i] if sign != 0 else []
        last_sign = sign
        if len(run) >= run_length:
            flagged.update(run)
    return flagged


def rule_k_of_m(values, upper: float, lower: float, k: int, m: int) -> set[int]:
    """`k` of `m` consecutive points beyond a zone boundary, same side."""
    flagged: set[int] = set()
    for start in range(0, len(values) - m + 1):
        window = range(start, start + m)
        upper_hits = [i for i in window if values[i] > upper]
        lower_hits = [i for i in window if values[i] < lower]
        if len(upper_hits) >= k:
            flagged.update(upper_hits)
        if len(lower_hits) >= k:
            flagged.update(lower_hits)
    return flagged
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rules.py -v`
Expected: PASS — all 5 tests green.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS — Task 2 and Task 3 tests all green.

- [ ] **Step 6: Commit**

```bash
git add xmr.py tests/test_rules.py
git commit -m "feat: XmR signal-detection rule functions"
```

---

### Task 4: Wire rules into `analyze()` (`xmr.py`)

**Files:**
- Modify: `xmr.py` (`analyze()` body + a private `_KOFM` config)
- Test: `tests/test_analyze_rules.py`

**Interfaces:**
- Consumes: `rule_1`, `rule_2`, `rule_k_of_m`, `_sigma_half_width`, `RULESETS`, `XmRResult` (Tasks 2–3)
- Produces: `analyze(values, ruleset=1, baseline=None)` now populates `violations` as a sorted `list[tuple[int, int, str]]` of `(point_index, rule_number, chart)` where `chart` is `"x"` or `"mr"`. X-chart rules run per the selected ruleset. The mR chart adds `(i, 1, "mr")` for every `i` in `1..n-1` where `moving_ranges[i] > mr_upper`. The list is sorted by natural tuple order.

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyze_rules.py`:

```python
import pytest

from xmr import analyze

# 10-point stable baseline: alternating 10/11, mR-bar = 1, X-bar = 10.5.
# Limits from baseline=(0,10): UNPL 13.16, LNPL 7.84.
# Sigma zones: 1s +/-0.8867, 1.5s +/-1.33, 2s +/-1.7733.
BASE = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11]


def test_ruleset_1_and_2_differ_on_same_series():
    full = BASE + [12, 12, 12]  # beyond 1.5s (11.83), not beyond 2s (12.27)
    r1 = analyze(full, ruleset=1, baseline=(0, 10))
    assert set(r1.violations) == {(10, 3, "x"), (11, 3, "x"), (12, 3, "x")}

    r2 = analyze(full, ruleset=2, baseline=(0, 10))
    assert r2.violations == []


def test_rule_1_flags_both_charts():
    full = BASE + [20]
    r = analyze(full, ruleset=1, baseline=(0, 10))
    assert set(r.violations) == {(10, 1, "x"), (10, 1, "mr")}


def test_point_can_carry_two_rules_and_nested_zone_counts():
    full = BASE + [12, 12, 20]
    r = analyze(full, ruleset=1, baseline=(0, 10))
    v = set(r.violations)
    assert (12, 1, "x") in v      # 20 is outside UNPL
    assert (12, 3, "x") in v      # ...and still counts toward "3 of 4 beyond 1.5s"
    assert (10, 3, "x") in v and (11, 3, "x") in v
    assert (12, 1, "mr") in v     # |20 - 12| = 8 > URL 3.268


def test_violations_are_sorted():
    full = BASE + [12, 12, 20]
    r = analyze(full, ruleset=1, baseline=(0, 10))
    assert r.violations == sorted(r.violations)


def test_constant_series_has_no_violations():
    r = analyze([7, 7, 7, 7, 7, 7], ruleset=2)
    assert r.violations == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_analyze_rules.py -v`
Expected: FAIL — `violations` is `[]` so the equality/`in` assertions fail.

- [ ] **Step 3: Update `analyze()` in `xmr.py`**

Add this module-level config near the other constants:

```python
# rule_number -> (k, m, k_sigma) for the "k of m beyond k-sigma" rules
_KOFM = {3: (3, 4, 1.5), 4: (2, 3, 2.0), 5: (4, 5, 1.0)}
```

Replace the `violations` placeholder line in `analyze()`:

```python
    violations: list[tuple[int, int, str]] = []  # rules wired in Task 4
```

with:

```python
    rules = RULESETS[ruleset]
    violations: list[tuple[int, int, str]] = []

    if 1 in rules:
        for i in rule_1(values, lnpl, unpl):
            violations.append((i, 1, "x"))
    if 2 in rules:
        for i in rule_2(values, x_center):
            violations.append((i, 2, "x"))
    for rule_num, (k, m, k_sigma) in _KOFM.items():
        if rule_num not in rules:
            continue
        half = _sigma_half_width(k_sigma, mr_center)
        hits = rule_k_of_m(values, x_center + half, x_center - half, k, m)
        for i in hits:
            violations.append((i, rule_num, "x"))

    for i in range(1, n):
        if moving_ranges[i] is not None and moving_ranges[i] > mr_upper:
            violations.append((i, 1, "mr"))

    violations.sort()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_analyze_rules.py -v`
Expected: PASS — all 5 tests green.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS — every test from Tasks 2–4 green.

- [ ] **Step 6: Commit**

```bash
git add xmr.py tests/test_analyze_rules.py
git commit -m "feat: run selected ruleset in analyze() and detect mR signals"
```

---

### Task 5: Streamlit UI (`app.py`)

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `analyze`, `RULESETS`, `MIN_POINTS`, `SOFT_LIMIT_MIN_MR` from `xmr` (Tasks 2–4)
- Produces:
  - `clean_series(df, time_col, value_col) -> tuple[list[str], list[float], int]` — returns `(labels, values, dropped_row_count)`. Coerces the value column with `pandas.to_numeric(errors="coerce")`, drops rows where the value is NaN, preserves order, stringifies labels.
  - `main() -> None` — the Streamlit script body, guarded by `if __name__ == "__main__": main()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_app.py`:

```python
import pandas as pd
import pytest

import app


def test_app_exposes_main():
    assert callable(app.main)


def test_clean_series_drops_non_numeric_and_missing_preserving_order():
    df = pd.DataFrame(
        {"t": ["a", "b", "c", "d", "e"], "v": [1, "oops", 3, None, 5]}
    )
    labels, values, dropped = app.clean_series(df, "t", "v")
    assert values == [1.0, 3.0, 5.0]
    assert labels == ["a", "c", "e"]
    assert dropped == 2


def test_clean_series_all_numeric():
    df = pd.DataFrame({"t": [1, 2, 3], "v": [10.0, 11.0, 12.0]})
    labels, values, dropped = app.clean_series(df, "t", "v")
    assert values == [10.0, 11.0, 12.0]
    assert labels == ["1", "2", "3"]
    assert dropped == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Write `app.py`**

```python
"""Streamlit UI for XmR control-chart analysis."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from xmr import MIN_POINTS, RULESETS, SOFT_LIMIT_MIN_MR, analyze

BLUE = "#1f77b4"
RED = "#d62728"
GREEN = "#2ca02c"


def clean_series(df, time_col, value_col):
    """Return (labels, values, dropped_count), keeping row order."""
    work = df[[time_col, value_col]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    n_before = len(work)
    work = work.dropna(subset=[value_col])
    dropped = n_before - len(work)
    labels = work[time_col].astype(str).tolist()
    values = [float(v) for v in work[value_col].tolist()]
    return labels, values, dropped


def _read_upload(uploaded):
    """Return a DataFrame from an uploaded .csv or .xlsx file."""
    if uploaded.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded)
    xls = pd.ExcelFile(uploaded)
    if len(xls.sheet_names) > 1:
        sheet = st.selectbox("Sheet", xls.sheet_names)
    else:
        sheet = xls.sheet_names[0]
    return pd.read_excel(xls, sheet_name=sheet)


def _marker_colors(n, flagged_indices):
    return [RED if i in flagged_indices else BLUE for i in range(n)]


def _hover_text(n, flags_by_index):
    out = []
    for i in range(n):
        rules = sorted(flags_by_index.get(i, ()))
        out.append(", ".join(f"Rule {r}" for r in rules) if rules else "")
    return out


def _x_chart(labels, result, x_flags):
    n = len(result.values)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=result.values,
            mode="lines+markers",
            line=dict(color=BLUE),
            marker=dict(color=_marker_colors(n, x_flags), size=8),
            text=_hover_text(n, x_flags),
            hovertemplate="%{x}<br>Value: %{y}<br>%{text}<extra></extra>",
            name="Value",
        )
    )
    fig.add_hline(y=result.x_center, line_color=GREEN,
                  annotation_text="X̄")
    fig.add_hline(y=result.unpl, line_color=RED, line_dash="dash",
                  annotation_text="UNPL")
    fig.add_hline(y=result.lnpl, line_color=RED, line_dash="dash",
                  annotation_text="LNPL")
    fig.update_layout(title="X chart (individual values)", height=380,
                      showlegend=False, margin=dict(t=40, b=20))
    return fig


def _mr_chart(labels, result, mr_flags):
    n = len(result.values)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=result.moving_ranges,
            mode="lines+markers",
            line=dict(color=BLUE),
            marker=dict(color=_marker_colors(n, mr_flags), size=8),
            text=_hover_text(n, mr_flags),
            hovertemplate="%{x}<br>Moving range: %{y}<br>%{text}<extra></extra>",
            name="Moving range",
            connectgaps=False,
        )
    )
    fig.add_hline(y=result.mr_center, line_color=GREEN,
                  annotation_text="mR̄")
    fig.add_hline(y=result.mr_upper, line_color=RED, line_dash="dash",
                  annotation_text="URL")
    fig.update_layout(title="mR chart (moving ranges)", height=300,
                      showlegend=False, margin=dict(t=40, b=20))
    return fig


def main():
    st.set_page_config(page_title="XmR Chart Analyzer", layout="wide")
    st.title("XmR Chart Analyzer")

    uploaded = st.file_uploader("Upload a CSV or Excel file",
                                type=["csv", "xlsx"])
    if uploaded is None:
        st.info(
            "Upload a CSV or Excel file to begin. The repo's `sample_data.csv` "
            "is a good first try (time column `week`, value column "
            "`measurement`)."
        )
        st.stop()

    try:
        df = _read_upload(uploaded)
    except Exception as exc:  # noqa: BLE001 - surface any parser message
        st.error(f"Could not read the file: {exc}")
        st.stop()

    if df.empty or len(df.columns) < 2:
        st.error("The file needs at least two columns and one row of data.")
        st.stop()

    st.subheader("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    columns = list(df.columns)
    c1, c2 = st.columns(2)
    time_col = c1.selectbox("Time / label column", columns, index=0)
    value_col = c2.selectbox(
        "Value column", columns, index=1 if len(columns) > 1 else 0
    )
    ruleset = st.radio(
        "Detection ruleset",
        options=list(RULESETS),
        format_func=lambda r: f"Ruleset {r}  (rules {', '.join(map(str, RULESETS[r]))})",
        horizontal=True,
    )

    labels, values, dropped = clean_series(df, time_col, value_col)
    if dropped:
        st.warning(f"Skipped {dropped} row(s) with missing or non-numeric values.")

    if len(values) < MIN_POINTS:
        st.error(
            f"XmR charts need at least {MIN_POINTS} data points; "
            f"got {len(values)}."
        )
        st.stop()

    try:
        result = analyze(values, ruleset=ruleset)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    mr_count = sum(1 for m in result.moving_ranges if m is not None)
    if mr_count < SOFT_LIMIT_MIN_MR:
        st.warning(
            f"Only {mr_count} moving ranges available. The limits are based on "
            "limited data and should be treated as soft (provisional) until "
            f"about {SOFT_LIMIT_MIN_MR + 1} data points are available."
        )
    if result.mr_center == 0:
        st.warning(
            "Every value is identical: the moving-range average is zero and the "
            "limits collapse onto the mean."
        )

    x_flags = defaultdict(set)
    mr_flags = defaultdict(set)
    for idx, rule, chart in result.violations:
        (x_flags if chart == "x" else mr_flags)[idx].add(rule)

    st.plotly_chart(_x_chart(labels, result, x_flags), use_container_width=True)
    st.plotly_chart(_mr_chart(labels, result, mr_flags), use_container_width=True)

    st.subheader("Signals")
    if result.violations:
        rows = [
            {
                "Point": labels[idx],
                "Chart": "X" if chart == "x" else "mR",
                "Value": result.values[idx]
                if chart == "x"
                else result.moving_ranges[idx],
                "Rule": rule,
            }
            for idx, rule, chart in result.violations
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.success("No signals detected — the process looks predictable.")

    signal_points = len({(idx, chart) for idx, _, chart in result.violations})
    st.caption(
        f"n = {len(values)}  |  X̄ = {result.x_center:.3f}  |  "
        f"mR̄ = {result.mr_center:.3f}  |  UNPL = {result.unpl:.3f}  |  "
        f"LNPL = {result.lnpl:.3f}  |  URL = {result.mr_upper:.3f}  |  "
        f"flagged points: {signal_points}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_app.py -v`
Expected: PASS — all 3 tests green.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS — every test green.

- [ ] **Step 6: Manual smoke test of the running app**

Run: `streamlit run app.py`
Then in the browser:
1. Upload `sample_data.csv`.
2. Confirm the preview table shows and column pickers default to `week` / `measurement`.
3. Confirm two charts render, the X chart shows red points among the last several weeks, and the signals table lists them.
4. Toggle the ruleset radio and confirm the flagged points change.
5. Confirm the summary caption shows n = 24 and non-zero limits.

Expected: all five behaviors hold, no traceback in the app or the terminal.

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: Streamlit UI with X and mR Plotly charts and signals table"
```

---

### Task 6: README finalization and push

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished app and test suite
- Produces: user-facing documentation; nothing other tasks depend on.

- [ ] **Step 1: Expand `README.md`**

```markdown
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
```

- [ ] **Step 2: Run the full suite one more time**

Run: `pytest -v`
Expected: PASS — every test green.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: full README for XmR Chart Analyzer"
```

- [ ] **Step 4: Push the branch**

```bash
git push -u origin feature/xmr-charts-v1
```

- [ ] **Step 5: Stop for the PR gate**

Do not open a pull request. Report to the user that `feature/xmr-charts-v1`
is pushed and ask whether to open a PR into `main`.

---

## Self-Review Notes

- **Spec coverage:** upload (T5), column selection (T5), all-data limits with
  `baseline` hook (T2), moving ranges / centers / limits (T2), rules 1–5 and
  both rulesets (T3–T4), k-of-m flags only qualifying points (T3), nested
  zones (T3–T4), mR chart rule 1 only (T4), two stacked Plotly charts (T5),
  signals table + summary line (T5), the four error/warning paths incl.
  `< 4` points and `< 17` moving ranges and degenerate constant series (T2,
  T5), tests enumerated in the spec (T2–T5), dependencies (T1), git workflow
  (Global Constraints + T1/T6). No gaps found.
- **Placeholder scan:** none — every code and test step is complete.
- **Type consistency:** `XmRResult` field order and names match between T2
  definition and T4/T5 use; `violations` tuple shape `(index, rule, chart)`
  is consistent T4→T5; `clean_series` return triple matches T5 test and
  `main()` use.
