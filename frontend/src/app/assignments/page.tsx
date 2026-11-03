"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { Assignment, apiRequest, errorMessage } from "@/lib/api";
import { formatDate, fromLocalInput } from "@/lib/dates";
import { useRequireAuth } from "@/lib/useRequireAuth";

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

  return (
    <>
      <section className="card">
        <h1>My assignments</h1>
        {error && <p className="error">{error}</p>}
        {assignments === null && !error && <p className="muted">Loading…</p>}
        {assignments && assignments.length === 0 && (
          <p className="muted">No assignments yet. Import from Canvas or add one below.</p>
        )}
        {assignments && assignments.length > 0 && (
          <ul className="list">
            {assignments.map((assignment) => (
              <li key={assignment.id}>
                <span>
                  <Link href={`/assignments/${assignment.id}`}>{assignment.title}</Link>{" "}
                  <span className="muted">· {assignment.course}</span>
                  <br />
                  <span className="muted">
                    {formatDate(assignment.deadline)} · {assignment.status.replace("_", " ")}
                  </span>
                </span>
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
          <button className="button" type="submit" disabled={busy}>
            Add assignment
          </button>
        </form>
      </section>
    </>
  );
}
