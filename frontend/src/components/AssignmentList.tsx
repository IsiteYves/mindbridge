import type { ReactNode } from "react";
import { Link } from "react-router";

import type { Assignment } from "@/lib/api";
import { formatDate } from "@/lib/dates";

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
