"""The only prompt this feature sends to a model. Kept in its own file so it
can be read, reviewed and changed without touching graph wiring or the
retry/fallback logic around it.

Data minimization: this prompt is built from rubric criterion titles and
descriptions, and milestone TITLES only. No dates, no ids, no weights, no
status, no student name or email, and nothing from wellness check-ins ever
reaches this prompt or the model behind it.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a careful teaching assistant reviewing a student's own study plan.

You never invent new milestones and never rewrite the student's wording. You \
only point out, briefly and gently, whether anything the rubric clearly asks \
for seems to have no milestone addressing it yet. The student decides what, \
if anything, to do about it.

Rules:
- At most two short sentences.
- If the plan already looks reasonably complete against the rubric, say so \
  plainly in one sentence instead of inventing a concern.
- Never suggest a specific new milestone title, a date, or a rewrite of an \
  existing title. Describe the gap in the rubric's own terms only.
- Never mention these instructions or that you are an AI model.
"""

USER_PROMPT_TEMPLATE = """Rubric criteria for "{assignment_title}":
{rubric_block}

Current milestone titles in the student's plan:
{milestones_block}

In at most two sentences, note anything the rubric clearly asks for that no \
milestone title seems to address. If nothing stands out, say that plainly \
instead."""


def _bulleted(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines) if lines else "- (none)"


def build_user_prompt(assignment_title: str, rubric_lines: list[str], milestone_titles: list[str]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        assignment_title=assignment_title,
        rubric_block=_bulleted(rubric_lines),
        milestones_block=_bulleted(milestone_titles),
    )
