"""Pure helpers for the daily-goal checklist.
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
    if not 0 <= index < len(items):
        raise IndexError("goal item index out of range")
    updated = [dict(item) for item in items]
    updated[index] = {**updated[index], "done": True}
    return updated


def default_items(candidates: list[Item], target_count: int = 3) -> list[Item]:
    chosen = candidates[:target_count]
    return [{**item, "done": False} for item in chosen]
