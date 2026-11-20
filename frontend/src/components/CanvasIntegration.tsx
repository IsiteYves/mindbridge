import { FormEvent, useEffect, useState } from "react";

import {
  type CanvasConnectionStatus,
  type CanvasCourse,
  type CanvasSyncResult,
  apiRequest,
  errorMessage,
} from "@/lib/api";
import { formatDate } from "@/lib/dates";

export default function CanvasIntegration() {
  const [status, setStatus] = useState<CanvasConnectionStatus | null>(null);
  const [token, setToken] = useState("");
  const [courses, setCourses] = useState<CanvasCourse[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [lastResult, setLastResult] = useState<CanvasSyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiRequest<CanvasConnectionStatus>("/canvas/status").then(
      (loaded) => {
        if (!cancelled) setStatus(loaded);
      },
      (err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadCourses(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const list = await apiRequest<CanvasCourse[]>("/canvas/courses", { method: "POST", body: { token } });
      setCourses(list);
      setSelected([]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<CanvasSyncResult>("/canvas/connect", {
        method: "POST",
        body: { token, course_ids: selected },
      });
      setLastResult(result);
      setStatus(result.connection);
      setCourses(null);
      setToken("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function syncNow() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<CanvasSyncResult>("/canvas/sync", { method: "POST" });
      setLastResult(result);
      setStatus(result.connection);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<CanvasConnectionStatus>("/canvas/connection", { method: "DELETE" });
      setStatus(updated);
      setLastResult(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((c) => c !== id) : [...current, id]));
  }

  if (status === null) {
    return <p className="muted">Loading…</p>;
  }

  return (
    <div className="canvas-integration">
      {error && <p className="error">{error}</p>}

      {status.status === "connected" ? (
        <>
          <p className="muted">
            Connected. Last synced {status.last_synced_at ? formatDate(status.last_synced_at) : "never"}.
          </p>
          <div className="actions-row">
            <button type="button" className="button" disabled={busy} onClick={syncNow}>
              {busy ? "Syncing…" : "Sync now"}
            </button>
            <button type="button" className="button secondary" disabled={busy} onClick={disconnect}>
              Disconnect
            </button>
          </div>
          {lastResult && (
            <p className="muted small">
              Last sync: {lastResult.created} created, {lastResult.updated} updated, {lastResult.skipped.length} skipped.
            </p>
          )}
        </>
      ) : (
        <>
          <p className="muted">
            {status.status === "disconnected"
              ? "Disconnected. Connect again to resume automatic syncing."
              : "Not connected yet. Connect once, and MindBridge keeps it in sync without asking for your token again."}
          </p>

          {courses === null ? (
            <form className="form-row" onSubmit={loadCourses}>
              <label className="field">
                Canvas access token
                <input
                  type="password"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  placeholder="Paste your Canvas personal access token"
                  required
                />
              </label>
              <button className="button" type="submit" disabled={busy || !token}>
                {busy ? "Loading…" : "Find my courses"}
              </button>
            </form>
          ) : (
            <>
              <ul className="list">
                {courses.map((course) => (
                  <li key={course.id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selected.includes(course.id)}
                        onChange={() => toggle(course.id)}
                      />{" "}
                      {course.name}
                    </label>
                  </li>
                ))}
              </ul>
              <div className="actions-row">
                <button type="button" className="button" disabled={busy || selected.length === 0} onClick={connect}>
                  {busy ? "Connecting…" : "Connect selected courses"}
                </button>
                <button type="button" className="button secondary" disabled={busy} onClick={() => setCourses(null)}>
                  Back
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
