import datetime as dt
from dataclasses import dataclass, field

STRESS_MIN = 1
STRESS_MAX = 5
DEFAULT_STRESS = 3

DEFAULT_DAILY_MINUTES = 120
MIN_DAILY_MINUTES = 30
MAX_DAILY_MINUTES = 480

DEFAULT_HORIZON_DAYS = 14
MAX_HORIZON_DAYS = 60

DEFAULT_BLOCKS_PER_MILESTONE = 2
MAX_BLOCKS_PER_MILESTONE = 8

DEFAULT_START_HOUR = 9
MAX_START_HOUR = 18
DAY_END_HOUR = 21
BREAK_MINUTES = 10

# Higher stress -> shorter blocks and a smaller share of the daily time budget.
BLOCK_MINUTES = {1: 50, 2: 50, 3: 45, 4: 30, 5: 25}
CAPACITY_FACTOR = {1: 1.0, 2: 1.0, 3: 0.9, 4: 0.6, 5: 0.4}


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


@dataclass
class Limits:
    block_minutes: int
    max_sessions_per_day: int

    @property
    def max_daily_study_minutes(self):
        return self.block_minutes * self.max_sessions_per_day


@dataclass
class Placement:
    milestone_id: int
    start: dt.datetime
    end: dt.datetime


@dataclass
class PlanResult:
    placements: list = field(default_factory=list)
    at_risk: list = field(default_factory=list)
    deferred: int = 0
    limits: Limits = None


def limits_for(stress_level, daily_minutes):
    #Work out block length and sessions per day for a stress level (1-5).
    block = BLOCK_MINUTES[stress_level]
    budget = int(daily_minutes * CAPACITY_FACTOR[stress_level])
    sessions = max(1, (budget + BREAK_MINUTES) // (block + BREAK_MINUTES))
    return Limits(block_minutes=block, max_sessions_per_day=sessions)


def adaptation_message(stress_level):
    if stress_level >= 4:
        return "Stress is high, so sessions are shorter and each day is lighter. Work is spread out to avoid stressful days."
    if stress_level == 3:
        return "Stress is moderate, so the daily load is slightly reduced."
    return "Stress is low, so sessions use the full planned length."


def _ceil_to_five_minutes(value):
    base = value.replace(second=0, microsecond=0)
    extra = (-base.minute) % 5
    if extra == 0 and base < value:
        extra = 5
    return base + dt.timedelta(minutes=extra)


class _Day:
    def __init__(self, date, tz, start_hour):
        self.date = date
        self.cursor = dt.datetime.combine(date, dt.time(start_hour), tzinfo=tz)
        self.limit = dt.datetime.combine(date, dt.time(DAY_END_HOUR), tzinfo=tz)
        self.count = 0


def plan_sessions(
    milestones,
    *,
    now,
    stress_level=DEFAULT_STRESS,
    daily_minutes=DEFAULT_DAILY_MINUTES,
    horizon_days=DEFAULT_HORIZON_DAYS,
    blocks_per_milestone=DEFAULT_BLOCKS_PER_MILESTONE,
    utc_offset_minutes=0,
    start_hour=DEFAULT_START_HOUR,
    completed_counts=None,
):
   
    completed_counts = completed_counts or {}
    tz = dt.timezone(dt.timedelta(minutes=utc_offset_minutes))
    limits = limits_for(stress_level, daily_minutes)
    result = PlanResult(limits=limits)

    local_now = now.astimezone(tz)
    today = local_now.date()
    days = [_Day(today + dt.timedelta(days=i), tz, start_hour) for i in range(horizon_days)]
    days[0].cursor = max(days[0].cursor, _ceil_to_five_minutes(local_now))

    def sort_key(milestone):
        return (milestone.target_date >= now, milestone.target_date, milestone.id)

    block = dt.timedelta(minutes=limits.block_minutes)
    rest = dt.timedelta(minutes=BREAK_MINUTES)

    for milestone in sorted(milestones, key=sort_key):
        overdue = milestone.target_date < now
        last_day = horizon_days - 1
        if not overdue:
            target_index = (milestone.target_date.astimezone(tz).date() - today).days
            if target_index > last_day:
                result.deferred += 1
                continue
            last_day = target_index

        needed = max(0, blocks_per_milestone - completed_counts.get(milestone.id, 0))
        placed = 0
        for _ in range(needed):
            best_index, best_key = None, None
            for index in range(last_day + 1):
                day = days[index]
                end = day.cursor + block
                if day.count >= limits.max_sessions_per_day or end > day.limit:
                    continue
                if not overdue and end > milestone.target_date:
                    continue
                key = (index,) if overdue else (day.count, index)
                if best_key is None or key < best_key:
                    best_index, best_key = index, key
            if best_index is None:
                break
            day = days[best_index]
            result.placements.append(Placement(milestone.id, day.cursor, day.cursor + block))
            day.cursor += block + rest
            day.count += 1
            placed += 1

        if placed < needed:
            reason = (
                "No free time left in the planning window for this overdue milestone."
                if overdue
                else "Not enough free time before the target date at the current daily load."
            )
            result.at_risk.append(
                {"milestone_id": milestone.id, "unscheduled_blocks": needed - placed, "reason": reason}
            )

    result.placements.sort(key=lambda p: (p.start, p.milestone_id))
    return result
