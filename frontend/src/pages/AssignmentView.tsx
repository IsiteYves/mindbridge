import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import MilestoneRail from "@/components/MilestoneRail";
import PlanReview from "@/components/PlanReview";
import WorkloadHeatmap from "@/components/WorkloadHeatmap";
import { Assignment, Milestone, RubricCriterion, Status, apiRequest, errorMessage } from "@/lib/api";
import { isPending } from "@/lib/assignments";
import { formatDate, fromLocalInput, toLocalInput } from "@/lib/dates";
import { toast } from "@/lib/toast";

const STATUS_OPTIONS: Status[] = ["not_started", "in_progress", "done"];
const STATUS_LABEL = (status: Status) => status.replace("_", " ");

type CriterionDraft = { title: string; weight: string };

function criteriaDrafts(rubric: RubricCriterion[] | undefined): CriterionDraft[] {
  if (!rubric || rubric.length === 0) return [{ title: "", weight: "" }];
  return rubric.map((criterion) => ({
    title: criterion.title,
    weight: criterion.weight == null ? "" : String(criterion.weight),
  }));
}

function parseWeight(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 100) return undefined;
  return parsed;
}

export default function AssignmentView({ id }: { id: string }) {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [criteria, setCriteria] = useState<CriterionDraft[]>([{ title: "", weight: "" }]);
  const [replace, setReplace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = assignment ? isPending(assignment) : true;

  const fetchAssignment = useCallback(
    () =>
      Promise.all([
        apiRequest<Assignment>(`/assignments/${id}`),
        apiRequest<Milestone[]>(`/assignments/${id}/milestones`),
      ]),
    [id],
  );

  function applyLoaded([loadedAssignment, loadedMilestones]: [Assignment, Milestone[]]) {
    setAssignment(loadedAssignment);
    setMilestones(loadedMilestones);
    setCriteria(criteriaDrafts(loadedAssignment.rubric));
  }

  useEffect(() => {
    let cancelled = false;
    fetchAssignment().then(
      (loaded) => {
        if (!cancelled) applyLoaded(loaded);
      },
      (err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [fetchAssignment]);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned: { title: string; weight: number | null }[] = [];
    for (const draft of criteria) {
      const title = draft.title.trim();
      if (!title) continue;
      const weight = parseWeight(draft.weight);
      if (weight === undefined) {
        toast.error(`"${title}" needs a weight from 0 to 100, or left blank.`);
        return;
      }
      cleaned.push({ title, weight });
    }
    setBusy(true);
    try {
      await apiRequest<Milestone[]>(`/assignments/${id}/milestones/from-rubric`, {
        method: "POST",
        body: { criteria: cleaned, replace },
      });
      setReplace(false);
      applyLoaded(await fetchAssignment());
      toast.success("Milestones generated from the rubric.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function updateCriterion(index: number, field: keyof CriterionDraft, value: string) {
    setCriteria(criteria.map((draft, i) => (i === index ? { ...draft, [field]: value } : draft)));
  }

  async function reorder(fromIndex: number, toIndex: number) {
    if (toIndex < 0 || toIndex >= milestones.length) return;
    const next = [...milestones];
    [next[fromIndex], next[toIndex]] = [next[toIndex], next[fromIndex]];
    try {
      const reordered = await apiRequest<Milestone[]>(`/assignments/${id}/milestones/order`, {
        method: "PUT",
        body: { milestone_ids: next.map((m) => m.id) },
      });
      setMilestones(reordered);
    } catch (err) {
      toast.error(errorMessage(err));
    }
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
        {assignment && !pending && (
          <p className="notice">This assignment is closed: it is submitted or its deadline has passed.</p>
        )}
      </section>

      <section className="card">
        <h2>Your route to submission</h2>
        <MilestoneRail milestones={milestones} deadline={assignment?.deadline ?? null} />
      </section>

      <section className="card">
        <h2>This assignment's workload</h2>
        <WorkloadHeatmap assignmentId={Number(id)} />
      </section>

      {pending && (
      <section className="card">
        <div className="card-title">
          <h2>Plan review</h2>
          <span className="muted">Advisory only — nothing here is applied unless you click Apply</span>
        </div>
        <PlanReview
          assignmentId={id}
          milestones={milestones}
          onMilestoneUpdated={(updated) =>
            setMilestones((current) => current.map((m) => (m.id === updated.id ? updated : m)))
          }
        />
      </section>
      )}

      {pending && (
      <section className="card">
        <h2>Rubric criteria</h2>
        <p className="muted">
          Each criterion becomes one milestone. Set a weight — the share of the rubric it covers — and milestones
          get proportional time instead of an even split; leave weight blank for an even split. Edit, add or remove
          criteria before generating.
        </p>
        <form className="form" onSubmit={generate}>
          {criteria.map((draft, index) => (
            <div className="form-row" key={index}>
              <label className="field">
                Criterion {index + 1}
                <input
                  value={draft.title}
                  onChange={(event) => updateCriterion(index, "title", event.target.value)}
                  maxLength={255}
                />
              </label>
              <label className="field field-weight">
                Weight %
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={draft.weight}
                  onChange={(event) => updateCriterion(index, "weight", event.target.value)}
                  placeholder="even"
                />
              </label>
              {criteria.length > 1 && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setCriteria(criteria.filter((_, i) => i !== index))}
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
              onClick={() => setCriteria([...criteria, { title: "", weight: "" }])}
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
          <button className="button" type="submit" disabled={busy || !pending}>
            {busy ? "Generating…" : "Generate milestones"}
          </button>
          {assignment && !assignment.deadline && (
            <p className="muted">
              This assignment has no deadline. <Link to="/assignments">Set one</Link> before generating milestones.
            </p>
          )}
        </form>
      </section>
      )}

      {pending && (
      <section className="card">
        <div className="card-title">
          <h2>Edit your plan</h2>
          <span className="pill">{milestones.length} milestones</span>
        </div>
        <p className="muted">
          This list is your own reading order — reordering it never changes a milestone's target date. The timeline
          above always reads by date.
        </p>
        {milestones.length === 0 && <p className="muted">No milestones yet. Generate from the rubric, or add one below.</p>}
        <ul className="list milestone-list">
          {milestones.map((milestone, index) => (
            <MilestoneRow
              key={milestone.id}
              milestone={milestone}
              isFirst={index === 0}
              isLast={index === milestones.length - 1}
              deadline={assignment?.deadline ?? null}
              onMoveUp={() => reorder(index, index - 1)}
              onMoveDown={() => reorder(index, index + 1)}
              onSaved={(saved) => setMilestones((current) => current.map((m) => (m.id === saved.id ? saved : m)))}
              onDeleted={(removedId) =>
                setMilestones((current) => current.filter((m) => m.id !== removedId))
              }
              onError={toast.error}
            />
          ))}
        </ul>
        <AddMilestoneForm
          assignmentId={id}
          deadline={assignment?.deadline ?? null}
          onAdded={(created) => setMilestones((current) => [...current, created])}
          onError={toast.error}
        />
      </section>
      )}
    </>
  );
}

function MilestoneRow({
  milestone,
  isFirst,
  isLast,
  deadline,
  onMoveUp,
  onMoveDown,
  onSaved,
  onDeleted,
  onError,
}: {
  milestone: Milestone;
  isFirst: boolean;
  isLast: boolean;
  deadline: string | null;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onSaved: (milestone: Milestone) => void;
  onDeleted: (id: number) => void;
  onError: (message: string) => void;
}) {
  const [title, setTitle] = useState(milestone.title);
  const [target, setTarget] = useState(toLocalInput(milestone.target_date));
  const [status, setStatus] = useState<Status>(milestone.status);
  const [weight, setWeight] = useState(milestone.weight == null ? "" : String(milestone.weight));
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedWeight = parseWeight(weight);
    if (parsedWeight === undefined) {
      onError(`"${title}" needs a weight from 0 to 100, or left blank.`);
      return;
    }
    setBusy(true);
    try {
      const saved = await apiRequest<Milestone>(`/milestones/${milestone.id}`, {
        method: "PATCH",
        body: { title, target_date: fromLocalInput(target), status, weight: parsedWeight },
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
    <li className="milestone-row">
      <div className="reorder-controls">
        <button
          type="button"
          className="reorder-button"
          disabled={isFirst || busy}
          onClick={onMoveUp}
          aria-label={`Move "${milestone.title}" earlier in the list`}
        >
          ↑
        </button>
        <button
          type="button"
          className="reorder-button"
          disabled={isLast || busy}
          onClick={onMoveDown}
          aria-label={`Move "${milestone.title}" later in the list`}
        >
          ↓
        </button>
      </div>
      <form className="form-row milestone-form" onSubmit={save}>
        <label className="field">
          Milestone
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} required />
        </label>
        <label className="field">
          Target date
          <input
            type="datetime-local"
            value={target}
            max={deadline ? toLocalInput(deadline) : undefined}
            onChange={(event) => setTarget(event.target.value)}
            required
          />
        </label>
        <label className="field field-weight">
          Weight %
          <input
            type="number"
            min={0}
            max={100}
            value={weight}
            onChange={(event) => setWeight(event.target.value)}
            placeholder="—"
          />
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

function AddMilestoneForm({
  assignmentId,
  deadline,
  onAdded,
  onError,
}: {
  assignmentId: string;
  deadline: string | null;
  onAdded: (milestone: Milestone) => void;
  onError: (message: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("");
  const [weight, setWeight] = useState("");
  const [busy, setBusy] = useState(false);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !target) return;
    const parsedWeight = parseWeight(weight);
    if (parsedWeight === undefined) {
      onError("Weight must be from 0 to 100, or left blank.");
      return;
    }
    setBusy(true);
    try {
      const created = await apiRequest<Milestone>(`/assignments/${assignmentId}/milestones`, {
        method: "POST",
        body: { title: title.trim(), target_date: fromLocalInput(target), weight: parsedWeight },
      });
      onAdded(created);
      setTitle("");
      setTarget("");
      setWeight("");
    } catch (err) {
      onError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="form-row add-milestone-form" onSubmit={add}>
      <label className="field">
        New milestone
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={255}
          placeholder="e.g. First draft"
        />
      </label>
      <label className="field">
        Target date
        <input
          type="datetime-local"
          value={target}
          max={deadline ? toLocalInput(deadline) : undefined}
          onChange={(event) => setTarget(event.target.value)}
        />
      </label>
      <label className="field field-weight">
        Weight %
        <input type="number" min={0} max={100} value={weight} onChange={(event) => setWeight(event.target.value)} placeholder="—" />
      </label>
      <button className="button" type="submit" disabled={busy || !title.trim() || !target}>
        {busy ? "Adding…" : "Add milestone"}
      </button>
    </form>
  );
}
