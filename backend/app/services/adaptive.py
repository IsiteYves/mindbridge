import datetime as dt

STRESS_WINDOW_DAYS = 7
RECENT_CHECKINS = 3
HIGH_STRESS = 4
ELEVATED_STRESS = 3
HIGH_STRESS_SLACK = 0.3
ELEVATED_STRESS_SLACK = 0.15


def stress_average(stress_levels):
    #Returns the mean of the given stress levels
    levels = list(stress_levels)
    if not levels:
        return None
    return sum(levels) / len(levels)


def slack_fraction(average):
    #Returns how much of the remaining time to hold back as slack
    if average is None:
        return 0.0
    if average >= HIGH_STRESS:
        return HIGH_STRESS_SLACK
    if average >= ELEVATED_STRESS:
        return ELEVATED_STRESS_SLACK
    return 0.0


def suggested_target(target, now, slack):
    #Pull a future target earlier by the slack fraction of the time remaining
    if target <= now:
        return target
    return now + (target - now) * (1 - slack)


def in_window(moment, now, hours):
    return now <= moment <= now + dt.timedelta(hours=hours)
