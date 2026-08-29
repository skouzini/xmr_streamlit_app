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
