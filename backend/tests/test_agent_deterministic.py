"""These test app/services/agent/deterministic.py directly"""

import datetime as dt

from app.services.agent import deterministic

NOW = dt.datetime(2026, 11, 10, 12, 0, tzinfo=dt.timezone.utc)
DEADLINE = dt.datetime(2026, 11, 20, 23, 59, tzinfo=dt.timezone.utc)


def milestone(id, title, status="not_started", weight=None, target_date=NOW, position=0):
    return {"id": id, "title": title, "description": None, "target_date": target_date, "status": status, "weight": weight, "position": position}


def criterion(title, weight, description=None):
    return {"title": title, "description": description, "weight": weight}


# ── check_balance

def test_a_heavily_weighted_uncovered_criterion_is_flagged():
    rubric = [criterion("Research methods", 40, "Interview stakeholders")]
    findings = deterministic.check_balance(rubric, [milestone(1, "Problem statement")])
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"
    assert findings[0]["milestone_id"] is None
    assert "Research methods" in findings[0]["message"]


def test_a_criterion_below_the_significance_threshold_is_never_flagged():
    rubric = [criterion("Minor formatting", 5)]
    findings = deterministic.check_balance(rubric, [])
    assert findings == []


def test_a_covered_criterion_with_a_matching_weight_is_silent():
    rubric = [criterion("Reflection", 30)]
    findings = deterministic.check_balance(rubric, [milestone(1, "Reflection draft", weight=28)])
    assert findings == []


def test_a_covered_criterion_with_a_mismatched_weight_is_flagged():
    rubric = [criterion("Reflection", 30)]
    findings = deterministic.check_balance(rubric, [milestone(1, "Reflection draft", weight=5)])
    assert len(findings) == 1
    assert findings[0]["milestone_id"] == 1
    assert "30%" in findings[0]["message"] and "5%" in findings[0]["message"]


def test_a_covered_criterion_with_no_weight_set_on_either_side_is_silent():
    # Nothing to compare: an unweighted plan is not penalised for being unweighted.
    rubric = [criterion("Reflection", 30)]
    findings = deterministic.check_balance(rubric, [milestone(1, "Reflection draft", weight=None)])
    assert findings == []


def test_a_criterion_with_no_weight_at_all_is_never_flagged():
    rubric = [criterion("Extra credit", None)]
    findings = deterministic.check_balance(rubric, [])
    assert findings == []


def test_all_milestones_done_adds_one_plain_finding():
    rubric = [criterion("Anything", 50)]
    findings = deterministic.check_balance(rubric, [milestone(1, "Anything done", status="done")])
    assert any("done" in f["message"].lower() for f in findings)


def test_balance_check_never_raises_on_an_empty_rubric_or_empty_plan():
    assert deterministic.check_balance([], []) == []


# ── detect_slipping


def test_an_overdue_not_done_milestone_is_slipping():
    milestones = [milestone(1, "Late", target_date=NOW - dt.timedelta(days=1))]
    assert deterministic.detect_slipping(milestones, NOW) == [1]


def test_an_overdue_done_milestone_is_not_slipping():
    milestones = [milestone(1, "Late but done", status="done", target_date=NOW - dt.timedelta(days=1))]
    assert deterministic.detect_slipping(milestones, NOW) == []


def test_a_future_milestone_is_not_slipping():
    milestones = [milestone(1, "Future", target_date=NOW + dt.timedelta(days=1))]
    assert deterministic.detect_slipping(milestones, NOW) == []


# ── propose_replan


def test_no_suggestion_when_nothing_remains_to_plan():
    suggestion, findings = deterministic.propose_replan(
        [milestone(1, "Done", status="done")], NOW, DEADLINE
    )
    assert suggestion is None
    assert findings == []


def test_no_suggestion_once_the_deadline_has_passed():
    milestones = [milestone(1, "Still open")]
    suggestion, findings = deterministic.propose_replan(milestones, NOW, NOW - dt.timedelta(hours=1))
    assert suggestion is None
    assert len(findings) == 1 and findings[0]["severity"] == "warning"


def test_a_valid_suggestion_covers_every_not_done_milestone_in_order():
    milestones = [
        milestone(1, "A", status="done"),
        milestone(2, "B"),
        milestone(3, "C"),
    ]
    suggestion, findings = deterministic.propose_replan(milestones, NOW, DEADLINE)
    assert findings == []
    assert suggestion["milestone_ids"] == [2, 3]
    assert len(suggestion["new_target_dates"]) == 2


def test_suggested_dates_are_strictly_increasing_and_inside_the_window():
    milestones = [milestone(1, "A"), milestone(2, "B"), milestone(3, "C")]
    suggestion, _ = deterministic.propose_replan(milestones, NOW, DEADLINE)
    dates = suggestion["new_target_dates"]
    assert all(NOW < d < DEADLINE for d in dates)
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)


def test_weighted_spacing_is_used_when_every_remaining_milestone_has_a_weight():
    milestones = [milestone(1, "Small", weight=10), milestone(2, "Big", weight=90)]
    suggestion, _ = deterministic.propose_replan(milestones, NOW, DEADLINE)
    first_span = suggestion["new_target_dates"][0] - NOW
    second_span = suggestion["new_target_dates"][1] - suggestion["new_target_dates"][0]
    assert second_span > first_span * 3


def test_falls_back_to_even_spacing_when_any_weight_is_missing():
    milestones = [milestone(1, "A", weight=90), milestone(2, "B", weight=None)]
    suggestion, findings = deterministic.propose_replan(milestones, NOW, DEADLINE)
    assert findings == []
    assert suggestion is not None


def test_a_deadline_too_close_to_fit_anything_falls_back_to_no_suggestion():
    milestones = [milestone(1, "A"), milestone(2, "B"), milestone(3, "C")]
    tight_deadline = NOW + dt.timedelta(seconds=1)
    suggestion, findings = deterministic.propose_replan(milestones, NOW, tight_deadline)
    assert suggestion is None
    assert len(findings) == 1 and findings[0]["severity"] == "warning"


def test_the_minimum_spacing_floor_is_enforced_at_its_exact_boundary():
    milestones = [milestone(1, "A"), milestone(2, "B"), milestone(3, "C")]
    minimum_total = dt.timedelta(hours=deterministic.MIN_HOURS_BETWEEN_TARGETS * 4)

    just_enough, _ = deterministic.propose_replan(milestones, NOW, NOW + minimum_total + dt.timedelta(minutes=1))
    assert just_enough is not None

    just_short, findings = deterministic.propose_replan(milestones, NOW, NOW + minimum_total - dt.timedelta(minutes=1))
    assert just_short is None
    assert findings[0]["severity"] == "warning"


def test_several_open_milestones_crowded_before_the_deadline_are_flagged():
    deadline = NOW + dt.timedelta(days=5)
    milestones = [
        {"id": 1, "title": "A", "description": None, "target_date": deadline - dt.timedelta(hours=20), "status": "not_started", "weight": None, "position": 0},
        {"id": 2, "title": "B", "description": None, "target_date": deadline - dt.timedelta(hours=30), "status": "not_started", "weight": None, "position": 1},
    ]
    findings = deterministic.check_crowding(milestones, deadline, NOW)
    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"


def test_spread_milestones_are_not_flagged_as_crowded():
    deadline = NOW + dt.timedelta(days=10)
    milestones = [
        {"id": 1, "title": "A", "description": None, "target_date": NOW + dt.timedelta(days=2), "status": "not_started", "weight": None, "position": 0},
        {"id": 2, "title": "B", "description": None, "target_date": NOW + dt.timedelta(days=6), "status": "not_started", "weight": None, "position": 1},
    ]
    assert deterministic.check_crowding(milestones, deadline, NOW) == []
