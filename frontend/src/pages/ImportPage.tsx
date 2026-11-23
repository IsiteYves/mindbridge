import { useEffect, useState } from "react";
import { Link } from "react-router";

import { type CanvasConnectionStatus, type CanvasSyncResult, apiRequest, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

export default function ImportPage() {
  const [status, setStatus] = useState<CanvasConnectionStatus | null>(null);
  const [result, setResult] = useState<CanvasSyncResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiRequest<CanvasConnectionStatus>("/canvas/status").then(setStatus, (err: unknown) =>
      toast.error(errorMessage(err)),
    );
  }, []);

  async function syncNow() {
    setBusy(true);
    try {
      const synced = await apiRequest<CanvasSyncResult>("/canvas/sync", { method: "POST" });
      setResult(synced);
      setStatus(synced.connection);
      toast.success("Canvas synced.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const connected = status?.status === "connected";

  return (
    <>
      <section className="card">
        <h1>Import from Canvas</h1>
        {status === null && <p className="muted">Loading…</p>}
        {status && !connected && (
          <>
            <p className="muted">Canvas is not connected. Connect it in Integrations first.</p>
            <Link to="/settings?section=integration" className="button">
              Connect Canvas
            </Link>
          </>
        )}
        {status && connected && (
          <>
            <p className="muted">
              Re-imports your selected courses with the stored Canvas connection. Last synced{" "}
              {status.last_synced_at ? formatDate(status.last_synced_at) : "never"}.
            </p>
            <div className="actions-row">
              <button type="button" className="button" disabled={busy} onClick={syncNow}>
                {busy ? "Syncing…" : "Sync now"}
              </button>
              <Link to="/settings?section=integration" className="button secondary">
                Change courses or token
              </Link>
            </div>
          </>
        )}
      </section>

      {result && (
        <section className="card">
          <h2>Sync finished</h2>
          <p>
            {result.created} created, {result.updated} updated, {result.skipped.length} skipped.
          </p>
          <ul className="list">
            {result.courses.map((course) => (
              <li key={course.id}>
                <span>
                  {course.name}
                  <br />
                  <span className="muted">
                    {course.found === 0
                      ? "Canvas returned no assignments for this course."
                      : `${course.pending} pending of ${course.found} · ${course.created} created · ${course.updated} updated · ${course.skipped} skipped`}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {result.skipped.length > 0 && (
            <details className="skipped-list">
              <summary className="muted small">Why {result.skipped.length} were skipped</summary>
              <ul className="list">
                {result.skipped.map((item) => (
                  <li key={item.canvas_id}>
                    <span>
                      {item.title} <span className="muted small">· {item.reason}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </>
  );
}
