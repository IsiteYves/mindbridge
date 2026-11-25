import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Pager } from "@/components/AssignmentList";
import { type FocusSession, apiRequest, errorMessage, type Page } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

const PAGE_SIZE = 15;

export default function FocusHistoryPage() {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page<FocusSession> | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiRequest<Page<FocusSession>>(`/focus-sessions?limit=${PAGE_SIZE}&offset=${offset}`).then(
      (result) => {
        if (!cancelled) setPage(result);
      },
      (err: unknown) => toast.error(errorMessage(err)),
    );
    return () => {
      cancelled = true;
    };
  }, [offset]);

  return (
    <section className="card">
      <div className="card-title">
        <h1>Focus history</h1>
        <Link to="/dashboard" className="button secondary compact">
          Back to dashboard
        </Link>
      </div>

      {page === null && <p className="muted">Loading…</p>}
      {page && page.total === 0 && <p className="empty-state">No focus sessions yet.</p>}
      {page && page.total > 0 && (
        <>
          <div className="focus-history">
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Planned</th>
                  <th>Focused</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((session) => (
                  <tr key={session.id}>
                    <td>{formatDate(session.started_at)}</td>
                    <td>{session.planned_minutes} min</td>
                    <td>{session.actual_minutes ?? "—"} min</td>
                    {/* "Running" means the session has no end time yet. */}
                    <td>{session.completed ? "Completed" : session.ended_at ? "Ended early" : "Running"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager offset={page.offset} limit={page.limit} total={page.total} onChange={setOffset} />
        </>
      )}
    </section>
  );
}
