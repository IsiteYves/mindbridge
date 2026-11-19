import { useEffect, useState } from "react";

import { type FocusSession, apiRequest, errorMessage } from "@/lib/api";

const PLANNED_MINUTES = 25;

function formatRemaining(seconds: number): string {
  const clamped = Math.max(0, seconds);
  const minutes = Math.floor(clamped / 60);
  const secs = clamped % 60;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function FocusTimerCard() {
  const [session, setSession] = useState<FocusSession | null>(null);
  const [remaining, setRemaining] = useState(PLANNED_MINUTES * 60);
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiRequest<FocusSession[]>("/focus-sessions/today").then(
      (sessions) => {
        if (!cancelled) setTodayCount(sessions.length);
      },
      () => {
        if (!cancelled) setTodayCount(null);
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function end(completed: boolean) {
    if (!session || busy) return;
    setBusy(true);
    try {
      await apiRequest<FocusSession>(`/focus-sessions/${session.id}/end`, {
        method: "PATCH",
        body: { completed },
      });
      setTodayCount((current) => (current ?? 0) + 1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSession(null);
      setBusy(false);
    }
  }

  // A one-second countdown driven by a chain of timeouts rather than a single
  // interval: each tick schedules only the next one, so there is nowhere for
  // the "it finished" side effect to run except here, exactly once, when
  // remaining actually reaches zero. Ending the session is itself async, but
  // by the time it resolves `session` is already null, so this effect cannot
  // re-fire the same ending twice.
  useEffect(() => {
    if (!session) return;
    if (remaining <= 0) {
      end(true); // the planned time ran out, so this session finished, not stopped early
      return;
    }
    const id = window.setTimeout(() => setRemaining((value) => value - 1), 1000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, remaining]);

  async function start() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await apiRequest<FocusSession>("/focus-sessions", {
        method: "POST",
        body: { planned_minutes: PLANNED_MINUTES },
      });
      setSession(created);
      setRemaining(PLANNED_MINUTES * 60);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const running = session !== null;

  return (
    <article className="card focus-timer-card">
      <div className="card-title">
        <h3 className="mono-label">Focus timer</h3>
        <span className="muted small">{PLANNED_MINUTES} min</span>
      </div>
      <p className="focus-clock mono-label">{formatRemaining(remaining)}</p>
      {error && <p className="error">{error}</p>}
      <div className="focus-timer-actions">
        {running ? (
          <button type="button" className="button secondary" disabled={busy} onClick={() => end(false)}>
            Stop
          </button>
        ) : (
          <button type="button" className="button" disabled={busy} onClick={start}>
            Start
          </button>
        )}
      </div>
      {todayCount !== null && (
        <p className="muted small">
          {todayCount} focus session{todayCount === 1 ? "" : "s"} today
        </p>
      )}
    </article>
  );
}
