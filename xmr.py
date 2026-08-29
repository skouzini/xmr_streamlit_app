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
