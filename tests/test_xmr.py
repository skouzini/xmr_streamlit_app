import pytest

from xmr import (
    MIN_POINTS,
    SOFT_LIMIT_MIN_MR,
    RULESETS,
    XmRResult,
    analyze,
)

SERIES_A = [10, 12, 11, 13, 10, 14, 12, 11]  # n=8, mR mean = 15/7
# median(SERIES_A) = 11.5 ; mR = [2,1,2,3,4,2,1] -> median 2, mean 15/7
MEAN_MULT, MEDIAN_MULT = 2.660, 3.145
MEAN_URL_MULT, MEDIAN_URL_MULT = 3.268, 3.865


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


def test_x_zone_bounds_ruleset_1_is_the_one_and_a_half_sigma_pair():
    r = analyze(SERIES_A, ruleset=1)
    half = 1.5 / 3 * 2.660 * (15 / 7)
    assert r.x_zone_bounds == pytest.approx(
        [11.625 - half, 11.625 + half]
    )


def test_x_zone_bounds_ruleset_2_is_the_one_and_two_sigma_pairs():
    r = analyze(SERIES_A, ruleset=2)
    one = 1.0 / 3 * 2.660 * (15 / 7)
    two = 2.0 / 3 * 2.660 * (15 / 7)
    assert r.x_zone_bounds == pytest.approx(
        [11.625 - two, 11.625 - one, 11.625 + one, 11.625 + two]
    )


def test_x_zone_bounds_collapse_on_degenerate_series():
    r = analyze([5, 5, 5, 5, 5], ruleset=2)
    assert r.x_zone_bounds == [5.0, 5.0, 5.0, 5.0]


def test_default_center_methods_are_mean():
    r = analyze(SERIES_A)
    assert r.x_center_method == "mean"
    assert r.mr_center_method == "mean"


def test_median_x_center_shifts_the_limit_midpoint_only():
    r = analyze(SERIES_A, x_center="median")
    assert r.x_center == pytest.approx(11.5)
    assert r.mr_center == pytest.approx(15 / 7)  # still mean mR
    assert r.unpl == pytest.approx(11.5 + MEAN_MULT * 15 / 7)
    assert r.lnpl == pytest.approx(11.5 - MEAN_MULT * 15 / 7)
    assert r.mr_upper == pytest.approx(MEAN_URL_MULT * 15 / 7)


def test_median_mr_center_changes_spread_scaling_and_url():
    r = analyze(SERIES_A, mr_center="median")
    assert r.x_center == pytest.approx(11.625)  # still mean X
    assert r.mr_center == pytest.approx(2.0)
    assert r.unpl == pytest.approx(11.625 + MEDIAN_MULT * 2.0)
    assert r.lnpl == pytest.approx(11.625 - MEDIAN_MULT * 2.0)
    assert r.mr_upper == pytest.approx(MEDIAN_URL_MULT * 2.0)


def test_full_median_xmr():
    r = analyze(SERIES_A, x_center="median", mr_center="median")
    assert r.x_center == pytest.approx(11.5)
    assert r.mr_center == pytest.approx(2.0)
    assert r.unpl == pytest.approx(11.5 + MEDIAN_MULT * 2.0)
    assert r.lnpl == pytest.approx(11.5 - MEDIAN_MULT * 2.0)
    assert r.mr_upper == pytest.approx(MEDIAN_URL_MULT * 2.0)
    assert r.x_center_method == "median"
    assert r.mr_center_method == "median"


def test_median_mr_center_scales_the_secondary_zones():
    r = analyze(SERIES_A, ruleset=1, mr_center="median")
    half = 1.5 / 3 * MEDIAN_MULT * 2.0
    assert r.x_zone_bounds == pytest.approx(
        [11.625 - half, 11.625 + half]
    )


def test_invalid_center_method_raises():
    with pytest.raises(ValueError):
        analyze(SERIES_A, x_center="mode")
    with pytest.raises(ValueError):
        analyze(SERIES_A, mr_center="avg")


def test_median_on_degenerate_series_still_collapses():
    r = analyze([5, 5, 5, 5, 5], x_center="median", mr_center="median")
    assert r.mr_center == 0
    assert r.x_center == r.unpl == r.lnpl == 5
    assert r.mr_upper == 0


def test_soft_limit_boundary_moving_range_counts():
    r18 = analyze(list(range(18)))
    assert len(r18.moving_ranges) == 18
    non_none_18 = sum(1 for m in r18.moving_ranges if m is not None)
    assert non_none_18 == 17 == SOFT_LIMIT_MIN_MR

    r17 = analyze(list(range(17)))
    non_none_17 = sum(1 for m in r17.moving_ranges if m is not None)
    assert non_none_17 == 16
    assert non_none_17 < SOFT_LIMIT_MIN_MR
