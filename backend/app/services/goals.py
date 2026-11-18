"""Pure helpers for the daily-goal checklist.

A DailyGoal's `items` column is a plain JSON list of dicts shaped like:
    {"label": str, "kind": "milestone" | "focus_session" | "custom",
     "ref_id": int | None, "done": bool}

Everything here takes that list in and returns a new list or a value out. No
Flask, no database session, no side effects — the API layer (added once the
goals endpoints land) owns persistence; these functions are what make that
layer's behaviour independently testable and reviewable.
"""

from __future__ import annotations

Item = dict


def progress(items: list[Item]) -> tuple[int, int]:
    """Return (done_count, total_count) for a goal's items."""
    items = items or []
    done = sum(1 for item in items if item.get("done"))
    return done, len(items)


def is_complete(items: list[Item]) -> bool:
    """A goal with no items is not complete; there is nothing to have finished."""
    done, total = progress(items)
    return total > 0 and done == total


def mark_done(items: list[Item], index: int) -> list[Item]:
    """Return a new list with item[index] marked done. Does not mutate the input.

    Raises IndexError if index is out of range; the API layer translates that
    into a 404 rather than silently ignoring an edit against a stale list.
    """
    if not 0 <= index < len(items):
        raise IndexError("goal item index out of range")
    updated = [dict(item) for item in items]
    updated[index] = {**updated[index], "done": True}
    return updated


def default_items(candidates: list[Item], target_count: int = 3) -> list[Item]:
    """Pick the day's checklist from a larger list of candidate tasks.

    Takes the first `target_count` candidates as given — the caller decides
    priority order (for example, soonest target date first) before calling
    this — and marks each `done: False`. A realistic, achievable goal beats a
    crowded one, so this never pads short lists or truncates silently beyond
    what the caller already prioritised.
    """
    chosen = candidates[:target_count]
    return [{**item, "done": False} for item in chosen]
