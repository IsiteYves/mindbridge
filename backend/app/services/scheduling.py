def milestone_targets(count, start, deadline):
    """Return `count` datetimes evenly spaced strictly between start and deadline."""
    span = deadline - start
    return [start + span * (index + 1) / (count + 1) for index in range(count)]


def weighted_targets(weights, start, deadline):
    """Space targets by effort rather than evenly."""
    count = len(weights)
    if count == 0:
        return []

    usable = [float(w) for w in weights if isinstance(w, (int, float)) and w > 0]
    # Falls back to even spacing when any weight is missing or not positive.
    if len(usable) != count:
        return milestone_targets(count, start, deadline)

    total = sum(usable)
    span = deadline - start
    targets = []
    running = 0.0
    for weight in usable:
        running += weight
        # Reserve the final slice so the last target sits before the deadline.
        fraction = running / (total * (count + 1) / count)
        targets.append(start + span * fraction)
    return targets
