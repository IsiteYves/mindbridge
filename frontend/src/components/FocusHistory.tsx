import { useEffect, useState } from "react";

import { Pager } from "@/components/AssignmentList";
import { type FocusSession, apiRequest, errorMessage, type Page } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

const PAGE_SIZE = 10;

export function FocusHistory() {
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

  if (page === null) return <p className="muted small">Loading history…</p>;
  if (page.total === 0) return <p className="muted small">No focus sessions yet.</p>;

  return (
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
              <td>{session.completed ? "Completed" : session.ended_at ? "Ended early" : "Running"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Pager offset={page.offset} limit={page.limit} total={page.total} onChange={setOffset} />
    </div>
  );
}
