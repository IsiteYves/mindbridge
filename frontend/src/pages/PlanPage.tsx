import { useEffect, useState } from "react";
import { Link } from "react-router";

import { apiRequest, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { isMoved, Reminder, Schedule, timeLeft } from "@/lib/schedule";

const SCHEDULE_PATH = "/schedule?days=14";
const REMINDERS_PATH = "/reminders?hours=72";

type PlanData = { schedule: Schedule; reminders: Reminder[] };

async function loadPlan(): Promise<PlanData> {
  const [schedule, reminders] = await Promise.all([
    apiRequest<Schedule>(SCHEDULE_PATH),
    apiRequest<Reminder[]>(REMINDERS_PATH),
  ]);
  return { schedule, reminders };
}

export default function PlanPage() {
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadPlan()
      .then((data) => {
        if (!cancelled) setPlan(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="card">
        <h1>Study plan</h1>
        <p className="error">{error}</p>
      </section>
    );
  }
  if (!plan) {
    return (
      <section className="card">
        <h1>Study plan</h1>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  const { schedule, reminders } = plan;
  const adjusted = schedule.slack_fraction > 0;
  const slackPercent = Math.round(schedule.slack_fraction * 100);

  return (
    <>
      <section className="card">
        <h1>Due in the next 3 days</h1>
        {reminders.length === 0 && <p className="muted">Nothing is due in the next 3 days.</p>}
        {reminders.length > 0 && (
          <ul className="list">
            {reminders.map((reminder) => (
              <li key={`${reminder.kind}-${reminder.id}`}>
                <strong>{reminder.kind === "deadline" ? "Deadline" : "Milestone"}:</strong> {reminder.title}{" "}
                <span className="muted">
                  ({reminder.course}, {timeLeft(reminder.hours_left)}, {formatDate(reminder.due_at)})
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h1>Upcoming milestones</h1>
        {schedule.stress_average === null ? (
          <p className="muted">
            Your dates are the ones you set. <Link to="/check-in">Save a daily check-in</Link> and MindBridge will
            leave more slack when stress is high.
          </p>
        ) : adjusted ? (
          <p className="muted">
            Recent check-ins average {schedule.stress_average.toFixed(1)} out of 5 stress. Each milestone is pulled
            earlier by {slackPercent}% of the time left, so there is more slack before the real deadline.
          </p>
        ) : (
          <p className="muted">
            Recent check-ins average {schedule.stress_average.toFixed(1)} out of 5 stress, so your dates are unchanged.
          </p>
        )}

        {schedule.milestones.length === 0 && <p className="muted">No open milestones in the next 14 days.</p>}
        {schedule.milestones.length > 0 && (
          <ul className="list">
            {schedule.milestones.map((milestone) => (
              <li key={milestone.id}>
                <strong>{milestone.title}</strong>{" "}
                <span className="muted">
                  ({milestone.course} · {milestone.assignment_title})
                </span>
                <div>
                  Work on it by {formatDate(milestone.suggested_date)}
                  {isMoved(milestone) && <span className="muted"> · was {formatDate(milestone.target_date)}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
