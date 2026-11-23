import type { ReactNode } from "react";
import { useState } from "react";
import { Link } from "react-router";

import { type Assignment, apiRequest, errorMessage, type Status } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

const STATUS_OPTIONS: { value: Status; label: string }[] = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
];

export function StatusSelect({ assignment, onChanged }: { assignment: Assignment; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);

  async function change(next: Status) {
    setBusy(true);
    try {
      await apiRequest(`/assignments/${assignment.id}`, { method: "PATCH", body: { status: next } });
      toast.success("Status updated.");
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <select
      className="status-select"
      aria-label={`Status of ${assignment.title}`}
      value={assignment.status}
      disabled={busy}
      onChange={(event) => change(event.target.value as Status)}
    >
      {STATUS_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function AssignmentList({
  items,
  badge,
}: {
  items: Assignment[];
  badge: (assignment: Assignment) => ReactNode;
}) {
  return (
    <ul className="list assignment-list">
      {items.map((assignment) => (
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
            {badge(assignment)}
            <Link to={`/assignments/${assignment.id}`} className="button secondary compact">
              View
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Pager({
  offset,
  limit,
  total,
  onChange,
}: {
  offset: number;
  limit: number;
  total: number;
  onChange: (nextOffset: number) => void;
}) {
  if (total <= limit) return null;
  const first = offset + 1;
  const last = Math.min(offset + limit, total);
  return (
    <div className="pager">
      <span className="muted small">
        {first}–{last} of {total}
      </span>
      <div className="assignment-actions">
        <button
          type="button"
          className="button secondary compact"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Previous
        </button>
        <button
          type="button"
          className="button secondary compact"
          disabled={offset + limit >= total}
          onClick={() => onChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
