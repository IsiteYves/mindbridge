"""Plan review: advisory only.

This reads a plan the student already wrote and the rubric it is assessed
against, and returns observations — never new milestones, never changed
dates, never anything auto-applied. A `replan_suggestion` is included when
one is available, but it is exactly that: a suggestion the student applies
by hand if they want it, through the same PATCH endpoints they already use
to edit any milestone.

This is the only function the rest of the backend should call; everything
else in this package is an implementation detail of how the review gets
built. See graph.py for the control flow and deterministic.py / llm.py for
what each step actually checks.
"""

from __future__ import annotations

import datetime as dt

from app.api.common import iso_utc
from app.services.agent.graph import run
from app.services.agent.state import MilestoneFacts, PlanReviewState, RubricCriterionFacts


def _rubric_facts(rubric: list[dict] | None) -> list[RubricCriterionFacts]:
    # Defensive against rubric JSON saved before weight existed on a criterion
    # (see the sprint that added it): .get rather than indexing.
    return [
        RubricCriterionFacts(
            title=criterion.get("title", ""),
            description=criterion.get("description"),
            weight=criterion.get("weight"),
        )
        for criterion in (rubric or [])
    ]


def _milestone_facts(milestones) -> list[MilestoneFacts]:
    return [
        MilestoneFacts(
            id=milestone.id,
            title=milestone.title,
            description=milestone.description,
            target_date=milestone.target_date,
            status=milestone.status,
            weight=milestone.weight,
            position=milestone.position,
        )
        for milestone in milestones
    ]


def review_plan(assignment, milestones, now: dt.datetime | None = None) -> dict:
    """`assignment` and `milestones` are the ORM objects (Assignment and its
    Milestone rows). Returns a plain, JSON-ready dict matching the API
    contract documented in app/api/agent.py.
    """
    initial_state = PlanReviewState(
        assignment_title=assignment.title,
        course=assignment.course,
        deadline=assignment.deadline,
        now=now or dt.datetime.now(dt.timezone.utc),
        rubric=_rubric_facts(assignment.rubric),
        milestones=_milestone_facts(milestones),
    )
    result = run(initial_state)

    suggestion = result.get("replan_suggestion")
    return {
        "generated_at": iso_utc(result["now"]),
        "summary": result["summary"],
        "findings": result["findings"],
        "replan_suggestion": (
            {
                "milestone_ids": suggestion["milestone_ids"],
                "new_target_dates": [iso_utc(target) for target in suggestion["new_target_dates"]],
            }
            if suggestion
            else None
        ),
    }
