import { FormEvent, useEffect, useState } from "react";

import { type CanvasConnectionStatus, type CanvasSyncResult, apiRequest, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import ConfirmDialog from "@/components/ConfirmDialog";
import { toast } from "@/lib/toast";

type Course = { id: string; name: string };

export default function CanvasIntegration() {
  const [status, setStatus] = useState<CanvasConnectionStatus | null>(null);
  const [token, setToken] = useState("");
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [usingNewToken, setUsingNewToken] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);

  useEffect(() => {
    apiRequest<CanvasConnectionStatus>("/canvas/status").then(setStatus, (err: unknown) =>
      toast.error(errorMessage(err)),
    );
  }, []);

  const connected = status?.status === "connected";

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((c) => c !== id) : [...current, id]));
  }

  // Shared wrapper: sets one busy flag and turns any thrown error into a toast.
  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function changeCourses() {
    return run(async () => {
      const list = await apiRequest<(Course & { selected: boolean })[]>("/canvas/courses/available");
      setCourses(list.map(({ id, name }) => ({ id, name })));
      setSelected(list.filter((course) => course.selected).map((course) => course.id));
      setUsingNewToken(false);
    });
  }

  function loadWithToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    return run(async () => {
      const list = await apiRequest<Course[]>("/canvas/courses", { method: "POST", body: { token } });
      setCourses(list);
      setSelected([]);
      setUsingNewToken(true);
    });
  }

  function saveSelection() {
    return run(async () => {
      const result = await apiRequest<CanvasSyncResult>("/canvas/courses/selection", {
        method: "PUT",
        body: { course_ids: selected },
      });
      setStatus(result.connection);
      setCourses(null);
      toast.success("Canvas courses saved and synced.");
    });
  }

  // A new token is saved and synced together with the chosen courses in one request.
  function connectWithToken() {
    return run(async () => {
      const result = await apiRequest<CanvasSyncResult>("/canvas/connect", {
        method: "POST",
        body: { token, course_ids: selected },
      });
      setStatus(result.connection);
      setCourses(null);
      setToken("");
      toast.success("Canvas connected.");
    });
  }

  function disconnect() {
    return run(async () => {
      const next = await apiRequest<CanvasConnectionStatus>("/canvas/connection", { method: "DELETE" });
      setStatus(next);
      setCourses(null);
      toast.success("Canvas disconnected. Imported assignments are kept.");
    });
  }

  const tokenForm = (
    <form className="form" onSubmit={loadWithToken}>
      <label className="field">
        Canvas access token
        <input
          type="password"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          autoComplete="off"
          required
        />
      </label>
      <div className="actions-row">
        <button aria-busy={busy} className="button" type="submit" disabled={busy || !token}>
          Load my courses
        </button>
      </div>
    </form>
  );

  return (
    <section className="card canvas-panel">
      <div className="card-title">
        <h2>Canvas</h2>
        <span className="pill">{connected ? "Connected" : "Not connected"}</span>
      </div>

      {status === null && <p className="muted">Loading…</p>}

      {status && connected && !courses && (
        <>
          <p className="muted">
            Last synced {status.last_synced_at ? formatDate(status.last_synced_at) : "never"}. Sync from Import from
            Canvas.
          </p>
          <div className="actions-row">
            <button aria-busy={busy} type="button" className="button secondary" disabled={busy} onClick={changeCourses}>
              Change courses
            </button>
            <button aria-busy={busy} type="button" className="button secondary" disabled={busy} onClick={() => setConfirmingDisconnect(true)}>
              Disconnect
            </button>
            <ConfirmDialog
              open={confirmingDisconnect}
              title="Disconnect Canvas?"
              message="Your stored token and course selection will be removed. Imported assignments are kept."
              confirmLabel="Disconnect"
              onConfirm={() => {
                setConfirmingDisconnect(false);
                void disconnect();
              }}
              onCancel={() => setConfirmingDisconnect(false)}
            />
          </div>
          <details className="token-change">
            <summary className="muted small">Use a different token</summary>
            {tokenForm}
          </details>
        </>
      )}

      {status && !connected && !courses && (
        <>
          <p className="muted">
            Paste a Canvas personal access token (Account → Settings → New Access Token). It is stored encrypted, so
            you can sync later without pasting it again.
          </p>
          {tokenForm}
        </>
      )}

      {courses && (
        <>
          <p className="muted">Choose the Canvas courses to sync.</p>
          {courses.length === 0 && <p className="muted">No active courses were found for this account.</p>}
          <ul className="list">
            {courses.map((course) => (
              <li key={course.id}>
                <label>
                  <input type="checkbox" checked={selected.includes(course.id)} onChange={() => toggle(course.id)} />{" "}
                  {course.name}
                </label>
              </li>
            ))}
          </ul>
          <div className="actions-row">
            <button aria-busy={busy}
              type="button"
              className="button"
              disabled={busy || selected.length === 0}
              onClick={usingNewToken ? connectWithToken : saveSelection}
            >
              {usingNewToken ? "Connect Canvas" : "Save courses"}
            </button>
            <button type="button" className="button secondary" onClick={() => setCourses(null)}>
              Cancel
            </button>
          </div>
        </>
      )}
    </section>
  );
}
