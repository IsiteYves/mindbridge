"""The plan-review route.

The reviewer is advisory only, by design: it reads a plan the student already
wrote and points out gaps, imbalance, or slipped dates against the rubric and
deadline.

Response shape:
    {
      "generated_at": "<ISO 8601 datetime>",
      "summary": "<one or two sentences>",
      "findings": [
        {
          "severity": "info" | "warning",
          "milestone_id": <int> | null,   // null means the finding is about the plan as a whole
          "message": "<one sentence, no instruction to act, no rewritten milestone>"
        }
      ],
      "replan_suggestion": null | {
        "milestone_ids": [<int>, ...],      // every not-done milestone, in their current list order
        "new_target_dates": [<ISO 8601>, ...]  // same length and order as milestone_ids; not applied anywhere
      }
    }
"""

from flask import Blueprint, jsonify

from app.api.assignments import owned_assignment_or_404
from app.api.auth import token_required
from app.services.agent import review_plan

agent_bp = Blueprint("agent", __name__)


@agent_bp.post("/assignments/<int:assignment_id>/milestones/review")
@token_required
def review_plan_route(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
    return jsonify(review_plan(assignment, assignment.milestones))
