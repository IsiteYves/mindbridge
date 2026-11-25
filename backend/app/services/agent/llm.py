"""The only module in this feature that calls out to a model provider.

Provider: Anthropic, via langchain-anthropic. Swapping providers later means
changing `_build_model` here — nothing in graph.py, deterministic.py, or the
route needs to know or care which provider answered.

Configuration is opt-in and silent when absent: no ANTHROPIC_API_KEY means
`configured()` returns False and the graph skips this node entirely, falling
back to the deterministic findings alone (see graph.py). This is deliberate:
the reviewer must be useful with zero spend, since a model key is something a
deployer adds later, not a requirement to use the feature at all.

Output is capped small on purpose: this call answers one narrow question in
at most two sentences, so there is no reason to budget for a long response —
smaller, cheaper, and faster to validate.
"""

from __future__ import annotations

import os

from app.services.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.agent.state import Finding, MilestoneFacts, RubricCriterionFacts

MAX_OUTPUT_TOKENS = 200
# A sentence or two should be well under this; anything longer than this is
# treated as the model ignoring the length instruction rather than displayed
# verbatim, since a runaway response is more likely to be unfocused than extra
# insight.
MAX_REPLY_CHARACTERS = 400


def configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _build_model():
    # Check what we can validate locally — a plain env var — before importing
    # the provider library, so a missing AGENT_MODEL gives a clear message
    # instead of surfacing as a raw ModuleNotFoundError on a deployment that
    # also hasn't installed the provider package yet.
    model_name = os.environ.get("AGENT_MODEL")
    if not model_name:
        raise RuntimeError("AGENT_MODEL is not set; see .env.example")

    # Imported lazily so that a deployment with no AI provider installed at
    # all (langchain-anthropic not even in the virtualenv) still imports and
    # runs this package fine; only calling this function requires the package.
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=model_name, max_tokens=MAX_OUTPUT_TOKENS, timeout=20, max_retries=0)


# Collapses whitespace and cuts overlong replies at a word boundary.
def _clean_reply(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > MAX_REPLY_CHARACTERS:
        cleaned = cleaned[:MAX_REPLY_CHARACTERS].rsplit(" ", 1)[0] + "…"
    return cleaned


def _call_once(assignment_title: str, rubric: list[RubricCriterionFacts], milestones: list[MilestoneFacts]) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    rubric_lines = [
        f"{criterion['title']}" + (f" — {criterion['description']}" if criterion["description"] else "")
        for criterion in rubric
    ]
    milestone_titles = [milestone["title"] for milestone in milestones]

    model = _build_model()
    response = model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=build_user_prompt(assignment_title, rubric_lines, milestone_titles)),
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    return _clean_reply(content)


def qualitative_review(
    assignment_title: str, rubric: list[RubricCriterionFacts], milestones: list[MilestoneFacts]
) -> tuple[list[Finding], bool, str | None]:
    """Returns (findings, attempted, error). `attempted` is False only when
    this was never called with credentials in the first place; once called,
    it is True whether or not the call ultimately succeeded, so a caller can
    always tell "skipped" apart from "tried and failed" from the return value
    alone, without reading logs.

    One retry on failure, then a clean, honest give-up: no finding at all
    beyond noting (via the caller's summary) that the AI-assisted pass did
    not run this time. A failure here never raises past this function and
    never blocks the deterministic findings from reaching the student.
    """
    if not configured():
        return [], False, None

    last_error: str | None = None
    for _ in range(2):
        try:
            reply = _call_once(assignment_title, rubric, milestones)
            if not reply:
                return [], True, None
            return (
                [Finding(severity="info", milestone_id=None, message=reply)],
                True,
                None,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any provider failure degrades the same way
            last_error = str(exc)
    return [], True, last_error
