"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { Assignment, Milestone, RubricCriterion, Status, apiRequest, errorMessage } from "@/lib/api";
import { formatDate, fromLocalInput, toLocalInput } from "@/lib/dates";
import { useRequireAuth } from "@/lib/useRequireAuth";

const STATUS_OPTIONS: Status[] = ["not_started", "in_progress", "done"];

const subscribeNever = () => () => {};

function readStoredRubricTitles(raw: string | null): string[] {
  try {
    const parsed = raw ? (JSON.parse(raw) as RubricCriterion[]) : [];
    return Array.isArray(parsed) && parsed.length > 0 ? parsed.map((criterion) => criterion.title) : [""];
  } catch {
    return [""];
  }
}

export default function AssignmentView({ id }: { id: string }) {
  useRequireAuth();
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const storedRaw = useSyncExternalStore(
    subscribeNever,
    () => {
      try {
        return sessionStorage.getItem(`mindbridge.rubric.${id}`);
      } catch {
        return null;
      }
    },
    () => null,
  );
  const [edits, setEdits] = useState<string[] | null>(null);
  const criteria = edits ?? readStoredRubricTitles(storedRaw);
  const [replace, setReplace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [loadedAssignment, loadedMilestones] = await Promise.all([
        apiRequest<Assignment>(`/assignments/${id}`),
        apiRequest<Milestone[]>(`/assignments/${id}/milestones`),
      ]);
      setAssignment(loadedAssignment);
      setMilestones(loadedMilestones);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiRequest<Assignment>(`/assignments/${id}`),
      apiRequest<Milestone[]>(`/assignments/${id}/milestones`),
    ]).then(
      ([loadedAssignment, loadedMilestones]) => {
        if (cancelled) return;
        setAssignment(loadedAssignment);
        setMilestones(loadedMilestones);
      },
      (err) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned = criteria
      .map((title) => title.trim())
      .filter(Boolean)
      .map((title) => ({ title }));
    setBusy(true);
    setError(null);
    try {
      await apiRequest<Milestone[]>(`/assignments/${id}/milestones/from-rubric`, {
        method: "POST",
        body: { criteria: cleaned, replace },
      });
      setReplace(false);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function updateCriterion(index: number, value: string) {
    setEdits(criteria.map((title, i) => (i === index ? value : title)));
  }

  return (
    <>
      <section className="card">
        <h1>{assignment?.title ?? "Assignment"}</h1>
        {assignment && (
          <p className="muted">
            {assignment.course} · due {formatDate(assignment.deadline)}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h2>Rubric criteria</h2>
        <p className="muted">
          Each criterion becomes one milestone, spread evenly between now and the deadline. Edit, add or remove criteria
          before generating.
        </p>
        <form className="form" onSubmit={generate}>
          {criteria.map((title, index) => (
            <div className="form-row" key={index}>
              <label className="field">
                Criterion {index + 1}
                <input value={title} onChange={(event) => updateCriterion(index, event.target.value)} maxLength={255} />
              </label>
              {criteria.length > 1 && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setEdits(criteria.filter((_, i) => i !== index))}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <div className="form-row">
            <button
              type="button"
              className="button secondary"
              onClick={() => setEdits([...criteria, ""])}
            >
              Add criterion
            </button>
            {milestones.length > 0 && (
              <label>
                <input type="checkbox" checked={replace} onChange={(event) => setReplace(event.target.checked)} />{" "}
                Replace existing milestones
              </label>
            )}
          </div>
          <button className="button" type="submit" disabled={busy || !assignment?.deadline}>
            {busy ? "Generating…" : "Generate milestones"}
          </button>
          {assignment && !assignment.deadline && (
            <p className="muted">
              This assignment has no deadline. <Link href="/assignments">Set one</Link> before generating milestones.
            </p>
          )}
        </form>
      </section>

      <section className="card">
        <h2>Milestones</h2>
        {milestones.length === 0 && <p className="muted">No milestones yet.</p>}
        <ul className="list">
          {milestones.map((milestone) => (
            <MilestoneRow
              key={milestone.id}
              milestone={milestone}
              onSaved={(saved) => setMilestones((current) => current.map((m) => (m.id === saved.id ? saved : m)))}
              onDeleted={(removedId) => setMilestones((current) => current.filter((m) => m.id !== removedId))}
              onError={setError}
            />
          ))}
        </ul>
      </section>
    </>
  );
}

const STATUS_LABEL = (status: Status) => status.replace("_", " ");

function MilestoneRow({
  milestone,
  onSaved,
  onDeleted,
  onError,
}: {
  milestone: Milestone;
  onSaved: (milestone: Milestone) => void;
  onDeleted: (id: number) => void;
  onError: (message: string) => void;
}) {
  const [title, setTitle] = useState(milestone.title);
  const [target, setTarget] = useState(toLocalInput(milestone.target_date));
  const [status, setStatus] = useState<Status>(milestone.status);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const saved = await apiRequest<Milestone>(`/milestones/${milestone.id}`, {
        method: "PATCH",
        body: { title, target_date: fromLocalInput(target), status },
      });
      onSaved(saved);
    } catch (err) {
      onError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await apiRequest(`/milestones/${milestone.id}`, { method: "DELETE" });
      onDeleted(milestone.id);
    } catch (err) {
      onError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <li>
      <form className="form-row" onSubmit={save} style={{ width: "100%" }}>
        <label className="field">
          Milestone
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} required />
        </label>
        <label className="field">
          Target
          <input type="datetime-local" value={target} onChange={(event) => setTarget(event.target.value)} required />
        </label>
        <label className="field">
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as Status)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {STATUS_LABEL(option)}
              </option>
            ))}
          </select>
        </label>
        <button className="button" type="submit" disabled={busy}>
          Save
        </button>
        <button className="button secondary" type="button" disabled={busy} onClick={remove}>
          Delete
        </button>
      </form>
    </li>
  );
}
