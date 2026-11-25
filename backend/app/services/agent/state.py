"""The state that flows through the plan-review graph (see graph.py).

Kept as one TypedDict so every node's input and output is explicit and
reviewable in one place, rather than scattered across function signatures.
Nothing here is a database model or an API response shape — assembling the
state from the database is gather.py's job, and serialising the final state
into the HTTP response is app/api/agent.py's job. This file only describes
the shape in between.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal, NotRequired, TypedDict


class RubricCriterionFacts(TypedDict):
    title: str
    description: str | None
    weight: int | None


class MilestoneFacts(TypedDict):
    id: int
    title: str
    description: str | None
    target_date: dt.datetime
    status: str
    weight: int | None
    position: int


class Finding(TypedDict):
    severity: Literal["info", "warning"]
    milestone_id: int | None
    message: str


class ReplanSuggestion(TypedDict):
    milestone_ids: list[int]
    new_target_dates: list[dt.datetime]


class PlanReviewState(TypedDict):
    # Input, set once by gather.py and never written again after.
    assignment_title: str
    course: str
    deadline: dt.datetime
    now: dt.datetime
    rubric: list[RubricCriterionFacts]
    milestones: list[MilestoneFacts]

    # Filled in by deterministic.py's nodes.
    balance_findings: NotRequired[list[Finding]]
    slipping_ids: NotRequired[list[int]]
    replan_suggestion: NotRequired[ReplanSuggestion | None]
    replan_findings: NotRequired[list[Finding]]

    # Filled in by llm.py's node. llm_attempted and llm_error exist so tests
    # and logs can tell "no key configured" apart from "the call failed" apart
    # from "the call succeeded but found nothing worth saying" — three states
    # that look identical from the outside (qualitative_findings is empty)
    # unless something records which one happened.
    qualitative_findings: NotRequired[list[Finding]]
    llm_attempted: NotRequired[bool]
    llm_error: NotRequired[str | None]

    # Filled in by the final compose node; this is what the route serialises.
    findings: NotRequired[list[Finding]]
    summary: NotRequired[str]
