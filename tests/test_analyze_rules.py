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
