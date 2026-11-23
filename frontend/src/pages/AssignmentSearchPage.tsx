import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import { Assignment, apiRequest, errorMessage } from "@/lib/api";
import { isPending } from "@/lib/assignments";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

type StateFilter = "all" | "pending" | "closed";

function stateLabel(assignment: Assignment): string {
  if (isPending(assignment)) return "Pending";
  return assignment.status === "done" ? "Submitted" : "Closed";
}

function startOfDay(value: string): number {
  return new Date(`${value}T00:00:00`).getTime();
}

function endOfDay(value: string): number {
  return new Date(`${value}T23:59:59.999`).getTime();
}

export default function AssignmentSearchPage() {
  const [assignments, setAssignments] = useState<Assignment[] | null>(null);
  const [query, setQuery] = useState("");
  const [state, setState] = useState<StateFilter>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [newestFirst, setNewestFirst] = useState(false);

  useEffect(() => {
    apiRequest<Assignment[]>("/assignments").then(setAssignments, (err: unknown) => toast.error(errorMessage(err)));
  }, []);

  const results = useMemo(() => {
    if (!assignments) return [];
    const needle = query.trim().toLowerCase();
    const filtered = assignments.filter((assignment) => {
      if (needle && !`${assignment.title} ${assignment.course}`.toLowerCase().includes(needle)) return false;
      if (state === "pending" && !isPending(assignment)) return false;
      if (state === "closed" && isPending(assignment)) return false;
      if (from || to) {
        if (!assignment.deadline) return false;
        const time = new Date(assignment.deadline).getTime();
        if (from && time < startOfDay(from)) return false;
        if (to && time > endOfDay(to)) return false;
      }
      return true;
    });
    const direction = newestFirst ? -1 : 1;
    return filtered.sort((a, b) => {
      if (!a.deadline && !b.deadline) return 0;
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return direction * (new Date(a.deadline).getTime() - new Date(b.deadline).getTime());
    });
  }, [assignments, query, state, from, to, newestFirst]);

  return (
    <section className="card">
      <div className="card-title">
        <h1>Search assignments</h1>
        <Link to="/assignments" className="button secondary compact">
          Back to my assignments
        </Link>
      </div>

      <div className="form-row">
        <label className="field">
          Name or course
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. Poster" />
        </label>
        <label className="field">
          Status
          <select value={state} onChange={(event) => setState(event.target.value as StateFilter)}>
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="closed">Closed or submitted</option>
          </select>
        </label>
      </div>

      <div className="form-row">
        <label className="field">
          Due from
          <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label className="field">
          Due to
          <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
        <label className="field">
          Order
          <select value={newestFirst ? "desc" : "asc"} onChange={(event) => setNewestFirst(event.target.value === "desc")}>
            <option value="asc">Earliest due first</option>
            <option value="desc">Latest due first</option>
          </select>
        </label>
      </div>

      <p className="muted small">{assignments === null ? "Loading…" : `${results.length} result${results.length === 1 ? "" : "s"}`}</p>

      {assignments && results.length === 0 && <p className="empty-state">No assignments match these filters.</p>}
      {results.length > 0 && (
        <ul className="list assignment-list">
          {results.map((assignment) => (
            <li key={assignment.id}>
              <div>
                <Link to={`/assignments/${assignment.id}`} className="list-title">
                  {assignment.title}
                </Link>
                <p className="muted">
                  {assignment.course} · {formatDate(assignment.deadline)}
                </p>
              </div>
              <div className="assignment-actions">
                <span className="pill">{stateLabel(assignment)}</span>
                <Link to={`/assignments/${assignment.id}`} className="button secondary compact">
                  View
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
