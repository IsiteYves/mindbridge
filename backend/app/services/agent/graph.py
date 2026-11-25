"""The plan-review graph.

    START -> balance -> slip -> [replan?] -> [qualitative?] -> compose -> END

Two conditional edges carry the actual branching logic this feature needs
LangGraph for, rather than a single flat function:

  - `replan` only runs when `slip` found something overdue and not done.
    Proposing new dates for a plan that is not behind schedule would be
    noise, not help.
  - `qualitative` only runs when an AI provider is configured (see llm.py).
    Skipping it is not a failure state: the deterministic findings from
    `balance` and `slip`/`replan` are a complete, useful result on their own.

Every node operates on plain data (see state.py) and has no Flask or database
dependency, so the graph can be built, compiled and run in a test with a
hand-built dict and no app context. Gathering that dict from the database is
__init__.py's job, not this file's.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.services.agent import deterministic, llm
from app.services.agent.state import Finding, PlanReviewState


def _balance_node(state: PlanReviewState) -> dict:
    return {
        "balance_findings": deterministic.check_balance(state["rubric"], state["milestones"])
        + deterministic.check_crowding(state["milestones"], state["deadline"], state["now"]),
    }


def _slip_node(state: PlanReviewState) -> dict:
    return {"slipping_ids": deterministic.detect_slipping(state["milestones"], state["now"])}


# Crowding near the deadline triggers a replan too, not only overdue milestones.
def _needs_replan(state: PlanReviewState) -> str:
    crowded = deterministic.check_crowding(state["milestones"], state["deadline"], state["now"])
    return "replan" if state.get("slipping_ids") or crowded else "qualitative_check"


def _replan_node(state: PlanReviewState) -> dict:
    suggestion, findings = deterministic.propose_replan(state["milestones"], state["now"], state["deadline"])
    return {"replan_suggestion": suggestion, "replan_findings": findings}


def _llm_is_configured(_state: PlanReviewState) -> str:
    return "qualitative" if llm.configured() else "compose"


def _qualitative_node(state: PlanReviewState) -> dict:
    findings, attempted, error = llm.qualitative_review(state["assignment_title"], state["rubric"], state["milestones"])
    return {"qualitative_findings": findings, "llm_attempted": attempted, "llm_error": error}


def _summarize(state: PlanReviewState, findings: list[Finding]) -> str:
    if not findings:
        if state.get("llm_error"):
            return "Rule-based checks found nothing to flag. AI-assisted review could not run this time."
        return "Milestones cover the rubric and finish before the deadline."

    warnings = sum(1 for f in findings if f["severity"] == "warning")
    info = len(findings) - warnings
    parts = []
    if warnings:
        parts.append(f"{warnings} thing{'s' if warnings != 1 else ''} worth addressing")
    if info:
        parts.append(f"{info} worth a look")
    note = " and ".join(parts).capitalize() + "."
    if state.get("llm_error"):
        note += " AI-assisted review could not run this time; these are rule-based."
    return note


def _compose_node(state: PlanReviewState) -> dict:
    findings = [
        *state.get("balance_findings", []),
        *state.get("replan_findings", []),
        *state.get("qualitative_findings", []),
    ]
    return {"findings": findings, "summary": _summarize(state, findings)}


def build_graph():
    graph = StateGraph(PlanReviewState)
    graph.add_node("balance", _balance_node)
    graph.add_node("slip", _slip_node)
    graph.add_node("replan", _replan_node)
    graph.add_node("qualitative", _qualitative_node)
    graph.add_node("compose", _compose_node)

    graph.add_edge(START, "balance")
    graph.add_edge("balance", "slip")
    graph.add_conditional_edges("slip", _needs_replan, {"replan": "replan", "qualitative_check": "qualitative_router"})
    # A tiny no-op router node, so both the "slipped" and "did not slip" paths
    # arrive at the same place before the second conditional edge decides
    # whether to call the model. LangGraph conditional edges route to a named
    # node, not to another conditional edge directly.
    graph.add_node("qualitative_router", lambda _state: {})
    graph.add_edge("replan", "qualitative_router")
    graph.add_conditional_edges("qualitative_router", _llm_is_configured, {"qualitative": "qualitative", "compose": "compose"})
    graph.add_edge("qualitative", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


_COMPILED = None


def get_compiled_graph():
    # Built once per process. The graph itself holds no request-specific or
    # database state, so there is nothing to reset between calls.
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_graph()
    return _COMPILED


def run(initial_state: PlanReviewState) -> PlanReviewState:
    return get_compiled_graph().invoke(initial_state)
