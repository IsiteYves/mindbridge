import { useEffect, useState } from "react";

import { Link } from "react-router";

import { type DailyGoal, apiRequest, errorMessage } from "@/lib/api";
import { useCurrentUser } from "@/lib/useCurrentUser";

function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}

function timeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function DailyGoalCard() {
  const [goal, setGoal] = useState<DailyGoal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingIndex, setSavingIndex] = useState<number | null>(null);
  const user = useCurrentUser();

  useEffect(() => {
    let cancelled = false;
    apiRequest<DailyGoal>("/daily-goal/today").then(
      (loaded) => {
        if (!cancelled) setGoal(loaded);
      },
      (err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function markDone(index: number) {
    setSavingIndex(index);
    setError(null);
    try {
      const updated = await apiRequest<DailyGoal>(`/daily-goal/today/items/${index}`, { method: "PATCH" });
      setGoal(updated);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSavingIndex(null);
    }
  }

  return (
    <article className="card daily-goal-card">
      <p className="mono-label">Today</p>
      <h2>
        {timeOfDayGreeting()}
        {user ? `, ${firstName(user.name)}` : ""}.
      </h2>
      <p className="muted">A little progress, daily.</p>
      {error && <p className="error">{error}</p>}

      {goal === null && !error && <p className="muted">Loading…</p>}

      {goal && goal.items.length === 0 && (
        <p className="empty-state">No open milestones to suggest yet. Generate a plan from an assignment's rubric.</p>
      )}

      {goal && goal.items.length > 0 && (
        <>
          <div className="goal-progress">
            <span className="mono-label">
              Daily goal {goal.done_count} / {goal.total_count}
            </span>
            <div className="goal-progress-bar">
              {goal.items.map((item, index) => (
                <span key={index} className={`goal-progress-segment${item.done ? " filled" : ""}`} />
              ))}
            </div>
          </div>
          <ul className="goal-items">
            {goal.items.map((item, index) => (
              <li key={index} className={item.done ? "done" : ""}>
                <label>
                  <input
                    type="checkbox"
                    checked={item.done}
                    disabled={item.done || savingIndex === index}
                    onChange={() => markDone(index)}
                  />
                  {item.label}
                </label>
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="actions-row">
        <Link to="/assignments" className="button secondary compact">
          View my assignments
        </Link>
      </div>
    </article>
  );
}
