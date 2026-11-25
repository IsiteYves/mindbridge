"""Everything the plan reviewer can say with no model call and no network.

Every function here is pure: given facts, return a result, nothing else. This
is deliberate. It means these checks run for every student regardless of
whether an AI provider is configured or paid for, they are exhaustively unit
testable without mocking a model, and they are the fallback the graph always
has even when the LLM step is skipped or fails. See graph.py for how these
compose with the one LLM-calling node.
"""

from __future__ import annotations

import datetime as dt

from app.services.scheduling import milestone_targets, weighted_targets
from app.services.agent.state import Finding, MilestoneFacts, ReplanSuggestion, RubricCriterionFacts

# A rubric criterion worth at least this much of the grade is significant
# enough to be worth a finding if the plan does not seem to reflect it.
SIGNIFICANT_WEIGHT = 20
# How close a milestone's own weight must be to its matching criterion's
# weight before the two are considered "roughly matching" rather than flagged.
WEIGHT_TOLERANCE = 10
# The least amount of working time between two targets for a suggestion to be
# worth proposing at all. Without this floor, a near deadline can produce
# dates that are technically ordered and technically inside the window but
# minutes apart — ordered, but not a plan a person could use.
MIN_HOURS_BETWEEN_TARGETS = 4

CROWD_WINDOW = dt.timedelta(hours=48)
CROWD_MIN_MILESTONES = 2
CROWD_MIN_REMAINING = dt.timedelta(hours=72)


def _title_words(title: str) -> set[str]:
    return {word for word in title.lower().split() if len(word) > 3}


def _mentions(milestone_title: str, criterion_title: str) -> bool:
    """A crude, transparent heuristic: do the two titles share a non-trivial
    word? This is intentionally simple rather than clever, so a student (or a
    reviewer of this code) can see exactly why a finding fired. It is used
    only to decide whether to raise an *info* finding, never a *warning* on
    its own, because a heuristic this simple will sometimes miss a real match
    (different wording) and should never scold a student for that.
    """
    return bool(_title_words(milestone_title) & _title_words(criterion_title))


def check_balance(rubric: list[RubricCriterionFacts], milestones: list[MilestoneFacts]) -> list[Finding]:
    """Compare what the rubric weights against what the plan's milestones
    actually weight and cover. Every finding here is phrased as an
    observation, not an instruction — "X is weighted heavily but..." rather
    than "add a milestone for X" — because the plan is the student's to
    write; this only points at a gap for them to decide what to do with.
    """
    findings: list[Finding] = []
    active = [m for m in milestones if m["status"] != "done"]

    for criterion in rubric:
        weight = criterion["weight"]
        if weight is None or weight < SIGNIFICANT_WEIGHT:
            continue

        covering = [m for m in milestones if _mentions(m["title"], criterion["title"])]
        if not covering:
            findings.append(
                Finding(
                    severity="info",
                    milestone_id=None,
                    message=(
                        f"\"{criterion['title']}\" is worth {weight}% of the rubric, and no milestone title "
                        "seems to cover it yet."
                    ),
                )
            )
            continue

        mismatched = [m for m in covering if m["weight"] is not None and abs(m["weight"] - weight) > WEIGHT_TOLERANCE]
        if mismatched and all(m["weight"] is not None for m in covering):
            findings.append(
                Finding(
                    severity="info",
                    milestone_id=covering[0]["id"],
                    message=(
                        f"\"{criterion['title']}\" carries {weight}% of the rubric, but its milestone is weighted "
                        f"{covering[0]['weight']}%. Giving it a matching weight spaces your plan to match."
                    ),
                )
            )

    if milestones and not active:
        findings.append(
            Finding(severity="info", milestone_id=None, message="Every milestone is marked done. Nothing left to balance.")
        )
    return findings


# Flags when several open milestones are packed into the final window before the deadline.
def check_crowding(milestones: list[MilestoneFacts], deadline: dt.datetime | None, now: dt.datetime) -> list[Finding]:
    if deadline is None or deadline - now < CROWD_MIN_REMAINING:
        return []
    window_start = deadline - CROWD_WINDOW
    crowded = [
        m for m in milestones if m["status"] != "done" and now < m["target_date"] and window_start <= m["target_date"] <= deadline
    ]
    if len(crowded) < CROWD_MIN_MILESTONES:
        return []
    return [
        Finding(
            severity="warning",
            milestone_id=None,
            message=(
                f"{len(crowded)} open milestones fall in the last two days before the deadline. "
                "Moving one earlier spreads the final stretch."
            ),
        )
    ]


def detect_slipping(milestones: list[MilestoneFacts], now: dt.datetime) -> list[int]:
    """Ids of milestones whose target date has passed without being done."""
    return [m["id"] for m in milestones if m["status"] != "done" and m["target_date"] < now]


# Targets must fall strictly inside the window and stay at least the minimum gap apart.
def _valid_targets(targets: list[dt.datetime], now: dt.datetime, deadline: dt.datetime) -> bool:
    if not targets:
        return False
    if any(not (now < target < deadline) for target in targets):
        return False
    min_gap = dt.timedelta(hours=MIN_HOURS_BETWEEN_TARGETS)
    if (targets[0] - now) < min_gap or (deadline - targets[-1]) < min_gap:
        return False
    return all(later - earlier >= min_gap for earlier, later in zip(targets, targets[1:]))


def propose_replan(
    milestones: list[MilestoneFacts], now: dt.datetime, deadline: dt.datetime
) -> tuple[ReplanSuggestion | None, list[Finding]]:
    """If any not-done milestone is re-spaceable, propose new target dates for
    every not-done milestone, in their current list order, from now to the
    deadline. Nothing is applied here or anywhere in this module — this
    returns a suggestion for the student to accept, adjust, or ignore.

    Tries weighted spacing first (when every remaining milestone has a
    weight), falls back to even spacing, and falls back again to no
    suggestion at all when neither produces a usable set of dates — most
    commonly because the deadline itself has already passed, or has too
    little time left for anything to fit before it.
    """
    remaining = [m for m in milestones if m["status"] != "done"]
    if not remaining:
        return None, []

    if now >= deadline:
        return None, [
            Finding(
                severity="warning",
                milestone_id=None,
                message="The assignment deadline has already passed, so no new plan can be suggested here.",
            )
        ]

    weights = [m["weight"] for m in remaining]
    attempts = (
        [weighted_targets(weights, now, deadline)] if all(w is not None for w in weights) else []
    ) + [milestone_targets(len(remaining), now, deadline)]

    for targets in attempts:
        if _valid_targets(targets, now, deadline):
            return (
                ReplanSuggestion(milestone_ids=[m["id"] for m in remaining], new_target_dates=targets),
                [],
            )

    return None, [
        Finding(
            severity="warning",
            milestone_id=None,
            message="There isn't enough time left before the deadline to safely re-space what's left. Consider moving the deadline or cutting scope instead.",
        )
    ]
