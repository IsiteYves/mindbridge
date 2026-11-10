import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { Assignment, Status, apiRequest, errorMessage } from "@/lib/api";
import { formatDate, fromLocalInput } from "@/lib/dates";
import { useRequireAuth } from "@/lib/useRequireAuth";

const STATUS_LABEL = (status: Status) => status.replace("_", " ");

function byDeadline(a: Assignment, b: Assignment) {
  if (!a.deadline && !b.deadline) return 0;
  if (!a.deadline) return 1;
  if (!b.deadline) return -1;
  return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
}

export default function AssignmentsPage() {
  useRequireAuth();
  const [assignments, setAssignments] = useState<Assignment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setAssignments(await apiRequest<Assignment[]>("/assignments"));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiRequest<Assignment[]>("/assignments").then(
      (list) => {
        if (!cancelled) setAssignments(list);
      },
      (err) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function addAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const deadline = String(form.get("deadline") ?? "");
    setBusy(true);
    setError(null);
    try {
      await apiRequest("/assignments", {
        method: "POST",
        body: {
          course: form.get("course"),
          title: form.get("title"),
          deadline: deadline ? fromLocalInput(deadline) : null,
        },
      });
      event.currentTarget.reset();
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const count = (status: Status) => assignments?.filter((a) => a.status === status).length ?? 0;
  const sorted = assignments ? [...assignments].sort(byDeadline) : [];

  return (
    <>
      <header className="page-header">
        <div className="stack">
          <p className="eyebrow">Dashboard</p>
          <h1>My assignments</h1>
          <p className="muted">Each rubric criterion becomes a milestone before the deadline.</p>
        </div>
        <Link to="/import" className="button">
          Import from Canvas
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="stats-grid" aria-label="Summary">
        <article className="stat">
          <p className="stat-label">Total</p>
          <p className="stat-value">{assignments?.length ?? "—"}</p>
          <p className="stat-detail">Tracked assignments</p>
        </article>
        <article className="stat todo">
          <p className="stat-label">Not started</p>
          <p className="stat-value">{count("not_started")}</p>
          <p className="stat-detail">Waiting to begin</p>
        </article>
        <article className="stat progress">
          <p className="stat-label">In progress</p>
          <p className="stat-value">{count("in_progress")}</p>
          <p className="stat-detail">Being worked on</p>
        </article>
        <article className="stat done">
          <p className="stat-label">Done</p>
          <p className="stat-value">{count("done")}</p>
          <p className="stat-detail">Submitted or finished</p>
        </article>
      </section>

      <section className="card">
        <div className="card-title">
          <h2>Upcoming</h2>
          <span className="muted">Sorted by deadline</span>
        </div>
        {assignments === null && !error && <p className="muted">Loading…</p>}
        {assignments && assignments.length === 0 && (
          <div className="empty-state">
            <p>No assignments yet.</p>
            <p className="muted">Import from Canvas or add one below.</p>
          </div>
        )}
        {sorted.length > 0 && (
          <ul className="list">
            {sorted.map((assignment) => (
              <li key={assignment.id}>
                <div>
                  <Link to={`/assignments/${assignment.id}`} className="list-title">
                    {assignment.title}
                  </Link>
                  <p className="muted">
                    {assignment.course} · {formatDate(assignment.deadline)}
                  </p>
                </div>
                <span className={`status-pill status-${assignment.status}`}>{STATUS_LABEL(assignment.status)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Add an assignment manually</h2>
        <form className="form" onSubmit={addAssignment}>
          <div className="form-row">
            <label className="field">
              Course
              <input name="course" required maxLength={255} />
            </label>
            <label className="field">
              Title
              <input name="title" required maxLength={255} />
            </label>
          </div>
          <label className="field">
            Deadline (optional)
            <input name="deadline" type="datetime-local" />
          </label>
          <div>
            <button className="button" type="submit" disabled={busy}>
              {busy ? "Adding…" : "Add assignment"}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
