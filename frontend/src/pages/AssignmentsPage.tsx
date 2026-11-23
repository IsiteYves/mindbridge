import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router";

import { AssignmentList, Pager } from "@/components/AssignmentList";
import DailyGoalCard from "@/components/DailyGoalCard";
import FocusTimerCard from "@/components/FocusTimerCard";
import WorkloadHeatmap from "@/components/WorkloadHeatmap";
import { type Assignment, apiRequest, errorMessage, type Page } from "@/lib/api";
import { fromLocalInput } from "@/lib/dates";
import { toast } from "@/lib/toast";

const PAGE_SIZE = 15;

type View = "pending" | "closed";

type Counts = { all: number; pending: number; inProgress: number; closed: number };

const NO_COUNTS: Counts = { all: 0, pending: 0, inProgress: 0, closed: 0 };

export default function AssignmentsPage() {
  const [view, setView] = useState<View>("pending");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState<Page<Assignment> | null>(null);
  const [counts, setCounts] = useState<Counts>(NO_COUNTS);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const countOf = (query: string) =>
      apiRequest<Page<Assignment>>(`/assignments?${query}&limit=1`).then(
        (result) => result.total,
        () => null,
      );
    apiRequest<Page<Assignment>>(`/assignments?state=${view}&limit=${PAGE_SIZE}&offset=${offset}`).then(
      (list) => {
        if (cancelled) return;
        if (!Array.isArray(list.items)) {
          setError("The server is out of date. Restart the MindBridge backend and reload.");
          return;
        }
        setPage(list);
        setError(null);
      },
      (err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    Promise.all([
      countOf("state=pending"),
      countOf("state=pending&status=in_progress"),
      countOf("state=closed"),
      countOf(""),
    ]).then(([pending, inProgress, closed, all]) => {
      if (cancelled) return;
      setCounts((current) => ({
        all: all ?? current.all,
        pending: pending ?? current.pending,
        inProgress: inProgress ?? current.inProgress,
        closed: closed ?? current.closed,
      }));
    });
    return () => {
      cancelled = true;
    };
  }, [view, offset, refresh]);

  function switchView() {
    setView((current) => (current === "pending" ? "closed" : "pending"));
    setOffset(0);
  }

  async function addAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const deadline = String(form.get("deadline") ?? "");
    setBusy(true);
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
      toast.success("Assignment added.");
      setRefresh((value) => value + 1);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div className="stack">
          <h1>My assignments</h1>
          <p className="muted">Each rubric criterion becomes a milestone before the deadline.</p>
        </div>
        <Link to="/import" className="button">
          Import from Canvas
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="dashboard-row" aria-label="Today">
        <DailyGoalCard />
        <FocusTimerCard />
      </section>

      <section className="stats-grid" aria-label="Summary">
        <article className="stat">
          <p className="stat-label">Total</p>
          <p className="stat-value">{counts.all}</p>
          <p className="stat-detail">Tracked assignments</p>
        </article>
        <article className="stat todo">
          <p className="stat-label">Pending</p>
          <p className="stat-value">{counts.pending}</p>
          <p className="stat-detail">Due ahead, not submitted</p>
        </article>
        <article className="stat progress">
          <p className="stat-label">In progress</p>
          <p className="stat-value">{counts.inProgress}</p>
          <p className="stat-detail">Being worked on</p>
        </article>
        <article className="stat done">
          <p className="stat-label">Closed</p>
          <p className="stat-value">{counts.closed}</p>
          <p className="stat-detail">Submitted or past deadline</p>
        </article>
      </section>

      <section className="card">
        <div className="card-title">
          <h2>Workload</h2>
          <span className="muted">How your work is spread across the month</span>
        </div>
        <WorkloadHeatmap />
      </section>

      <section className="card">
        <div className="card-title">
          <h2>{view === "pending" ? "Upcoming" : "Closed"}</h2>
          <span className="muted">
            {view === "pending" ? "Pending, sorted by deadline" : "Submitted or past deadline"}
          </span>
          <Link to="/assignments/search" className="button secondary compact">
            Search all
          </Link>
        </div>
        <button type="button" className="button secondary compact" onClick={switchView}>
          {view === "pending" ? `Show closed (${counts.closed})` : "Show pending"}
        </button>
        {page === null && !error && <p className="muted">Loading…</p>}
        {page && counts.all === 0 && (
          <div className="empty-state">
            <p>No assignments yet.</p>
            <p className="muted">Import from Canvas or add one below.</p>
          </div>
        )}
        {page && page.items.length === 0 && counts.all > 0 && (
          <p className="empty-state">Nothing here yet.</p>
        )}
        {page && page.items.length > 0 && (
          <>
            <AssignmentList
              items={page.items}
              badge={(a) => (
                <span className={`status-text status-${a.status}`}>{a.status.replace("_", " ")}</span>
              )}
            />
            <Pager offset={page.offset} limit={page.limit} total={page.total} onChange={setOffset} />
          </>
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
            Deadline
            <input name="deadline" type="datetime-local" required />
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
