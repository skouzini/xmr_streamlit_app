"""Pure XmR (individuals + moving range) control-chart statistics.

No Streamlit import here — this module is unit-tested in isolation.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

MIN_POINTS = 4
SOFT_LIMIT_MIN_MR = 17

CENTER_METHODS = ("mean", "median")
# 3-sigma multiplier on the mR centerline for the X-chart limits, and the
# upper-range-limit multiplier for the mR chart. The pair depends on whether
# the mR centerline is the mean or the median moving range (Wheeler's
# median-XmR factors: 3.145 = 3 / 0.9539, 3.865 = 3.687 / 0.9539).
_X_LIMIT_MULT = {"mean": 2.660, "median": 3.145}
_MR_UPPER_MULT = {"mean": 3.268, "median": 3.865}

RULESETS = {1: (1, 2, 3), 2: (1, 2, 4, 5)}
# rule_number -> (k, m, k_sigma) for the "k of m beyond k-sigma" rules
_KOFM = {3: (3, 4, 1.5), 4: (2, 3, 2.0), 5: (4, 5, 1.0)}


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
    # y-values of the secondary detection zones the active ruleset uses on the
    # X chart (rule 3 -> +/-1.5 sigma; rules 4 & 5 -> +/-1 and +/-2 sigma).
    # Sorted ascending; empty when the ruleset has no k-of-m rules.
    x_zone_bounds: list[float]
    x_center_method: str = "mean"
    mr_center_method: str = "mean"


def _sigma_half_width(k_sigma: float, mr_center: float, limit_mult: float) -> float:
    """Half-width of the k-sigma zone on the X chart."""
    return k_sigma / 3.0 * limit_mult * mr_center


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


def analyze(
    values,
    ruleset: int = 1,
    baseline=None,
    x_center: str = "mean",
    mr_center: str = "mean",
) -> XmRResult:
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
    for name, method in (("x_center", x_center), ("mr_center", mr_center)):
        if method not in CENTER_METHODS:
            raise ValueError(
                f"Unknown {name} method {method!r}; "
                f"expected one of {CENTER_METHODS}."
            )
    x_center_method, mr_center_method = x_center, mr_center

    moving_ranges: list[float | None] = [None] + [
        abs(values[i] - values[i - 1]) for i in range(1, n)
    ]

    if baseline is None:
        b_start, b_end = 0, n
    else:
        b_start, b_end = baseline
        if not (0 <= b_start < b_end <= n):
            raise ValueError(
                f"baseline {baseline!r} is outside the data (0..{n})."
            )
    if b_end - b_start < 2:
        raise ValueError("baseline must span at least 2 points.")

    base_values = values[b_start:b_end]
    base_mr = [
        abs(base_values[i] - base_values[i - 1])
        for i in range(1, len(base_values))
    ]
    _agg = {"mean": statistics.fmean, "median": statistics.median}
    x_center = _agg[x_center_method](base_values)
    mr_center = _agg[mr_center_method](base_mr)

    limit_mult = _X_LIMIT_MULT[mr_center_method]
    unpl = x_center + limit_mult * mr_center
    lnpl = x_center - limit_mult * mr_center
    mr_upper = _MR_UPPER_MULT[mr_center_method] * mr_center

    rules = RULESETS[ruleset]
    violations: list[tuple[int, int, str]] = []
    zone_halves: list[float] = []

    if 1 in rules:
        for i in rule_1(values, lnpl, unpl):
            violations.append((i, 1, "x"))
    if 2 in rules:
        for i in rule_2(values, x_center):
            violations.append((i, 2, "x"))
    for rule_num, (k, m, k_sigma) in _KOFM.items():
        if rule_num not in rules:
            continue
        half = _sigma_half_width(k_sigma, mr_center, limit_mult)
        zone_halves.append(half)
        hits = rule_k_of_m(values, x_center + half, x_center - half, k, m)
        for i in hits:
            violations.append((i, rule_num, "x"))

    x_zone_bounds = sorted(
        [x_center - h for h in zone_halves]
        + [x_center + h for h in zone_halves]
    )

    for i in range(1, n):
        if moving_ranges[i] is not None and moving_ranges[i] > mr_upper:
            violations.append((i, 1, "mr"))

    violations.sort()

    return XmRResult(
        values=values,
        moving_ranges=moving_ranges,
        x_center=x_center,
        unpl=unpl,
        lnpl=lnpl,
        mr_center=mr_center,
        mr_upper=mr_upper,
        violations=violations,
        x_zone_bounds=x_zone_bounds,
        x_center_method=x_center_method,
        mr_center_method=mr_center_method,
    )
