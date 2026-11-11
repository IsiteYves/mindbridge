def milestone_targets(count, start, deadline):
    """Return `count` datetimes evenly spaced strictly between start and deadline."""
    span = deadline - start
    return [start + span * (index + 1) / (count + 1) for index in range(count)]
