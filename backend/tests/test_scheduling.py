import datetime as dt

from app.services.scheduling import milestone_targets

START = dt.datetime(2026, 11, 3, 12, 0, tzinfo=dt.timezone.utc)
DEADLINE = dt.datetime(2026, 11, 13, 12, 0, tzinfo=dt.timezone.utc)


def test_targets_are_ordered_and_strictly_inside_the_window():
    targets = milestone_targets(4, START, DEADLINE)

    assert len(targets) == 4
    assert targets == sorted(targets)
    assert all(START < target < DEADLINE for target in targets)


def test_targets_are_evenly_spaced():
    targets = milestone_targets(3, START, DEADLINE)

    gaps = {targets[1] - targets[0], targets[2] - targets[1]}
    assert len(gaps) == 1
    assert targets[0] - START == targets[1] - targets[0]


def test_single_criterion_lands_in_the_middle():
    (target,) = milestone_targets(1, START, DEADLINE)

    assert target == START + (DEADLINE - START) / 2
