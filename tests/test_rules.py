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
