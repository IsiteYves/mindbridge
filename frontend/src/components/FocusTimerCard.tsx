import { useCallback, useEffect, useRef, useState } from "react";

import { FocusHistory } from "@/components/FocusHistory";
import { type FocusSession, apiRequest, errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";

const PRESETS = [15, 25, 45, 60];
const DEFAULT_MINUTES = 25;

function formatRemaining(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function resultText(result: FocusSession): string {
  const focused = result.actual_minutes ?? 0;
  if (result.completed) return `Completed: ${focused} of ${result.planned_minutes} min.`;
  return `Ended early: you focused ${focused} of ${result.planned_minutes} min.`;
}

async function fetchTodayCount(): Promise<number | null> {
  try {
    const sessions = await apiRequest<FocusSession[]>("/focus-sessions/today");
    return sessions.filter((session) => session.ended_at !== null).length;
  } catch {
    return null;
  }
}

export default function FocusTimerCard() {
  const [session, setSession] = useState<FocusSession | null>(null);
  const [endsAt, setEndsAt] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [minutes, setMinutes] = useState(DEFAULT_MINUTES);
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const [result, setResult] = useState<FocusSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const remaining = session ? Math.max(0, Math.ceil((endsAt - now) / 1000)) : minutes * 60;

  useEffect(() => {
    let cancelled = false;
    apiRequest<{ session: FocusSession | null }>("/focus-sessions/active").then(
      ({ session: active }) => {
        if (cancelled || !active) return;
        setSession(active);
        setEndsAt(Date.now() + (active.remaining_seconds ?? 0) * 1000);
      },
      () => undefined,
    );
    fetchTodayCount().then((count) => {
      if (!cancelled) setTodayCount(count);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const endingRef = useRef(false);

  const endSession = useCallback(async (id: number) => {
    if (endingRef.current) return;
    endingRef.current = true;
    setBusy(true);
    try {
      const ended = await apiRequest<FocusSession>(`/focus-sessions/${id}/end`, { method: "PATCH", body: {} });
      setResult(ended);
      setSession(null);
      setTodayCount(await fetchTodayCount());
    } catch (err) {
      toast.error(errorMessage(err));
      setSession(null);
    } finally {
      endingRef.current = false;
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    const id = window.setInterval(() => {
      const current = Date.now();
      setNow(current);
      if (current >= endsAt) void endSession(session.id);
    }, 1000);
    return () => window.clearInterval(id);
  }, [session, endsAt, endSession]);

  async function start() {
    setBusy(true);
    try {
      const created = await apiRequest<FocusSession>("/focus-sessions", {
        method: "POST",
        body: { planned_minutes: minutes },
      });
      setResult(null);
      setEndsAt(Date.now() + created.planned_minutes * 60 * 1000);
      setNow(Date.now());
      setSession(created);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="card focus-timer-card">
      <div className="card-title">
        <h3 className="mono-label">Focus timer</h3>
        {session ? (
          <span className="muted small">{session.planned_minutes} min</span>
        ) : (
          <select
            aria-label="Session length"
            value={minutes}
            disabled={busy}
            onChange={(event) => setMinutes(Number(event.target.value))}
          >
            {PRESETS.map((preset) => (
              <option key={preset} value={preset}>
                {preset} min
              </option>
            ))}
          </select>
        )}
      </div>
      <p className="focus-clock mono-label">{formatRemaining(remaining)}</p>
      {result && !session && <p className="notice">{resultText(result)}</p>}
      <div className="focus-timer-actions">
        {session ? (
          <button type="button" className="button secondary" disabled={busy} onClick={() => endSession(session.id)}>
            Stop
          </button>
        ) : (
          <button type="button" className="button" disabled={busy} onClick={start}>
            Start
          </button>
        )}
        <button type="button" className="button secondary compact" onClick={() => setHistoryOpen((open) => !open)}>
          {historyOpen ? "Hide history" : "History"}
        </button>
      </div>
      {todayCount !== null && (
        <p className="muted small">
          {todayCount} focus session{todayCount === 1 ? "" : "s"} ended today
        </p>
      )}
      {historyOpen && <FocusHistory />}
    </article>
  );
}
