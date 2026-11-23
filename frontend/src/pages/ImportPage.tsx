import { FormEvent, useState } from "react";
import { Link } from "react-router";

import { apiRequest, CanvasCourse, errorMessage, ImportResult } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { toast } from "@/lib/toast";

export default function ImportPage() {
  const [token, setCanvasToken] = useState("");
  const [courses, setCourses] = useState<CanvasCourse[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadCourses(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const list = await apiRequest<CanvasCourse[]>("/canvas/courses", { method: "POST", body: { token } });
      setCourses(list);
      setSelected([]);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function importSelected() {
    setBusy(true);
    try {
      const imported = await apiRequest<ImportResult>("/canvas/import", {
        method: "POST",
        body: { token, course_ids: selected },
      });
      setResult(imported);
      setCourses(null);
      setCanvasToken("");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((c) => c !== id) : [...current, id]));
  }

  const allSelected = courses !== null && courses.length > 0 && selected.length === courses.length;

  function toggleAll() {
    setSelected(allSelected || !courses ? [] : courses.map((course) => course.id));
  }

  return (
    <>
      <section className="card">
        <h1>Import from Canvas</h1>
        <p className="muted">
          Paste a Canvas personal access token (Account → Settings → New Access Token). It is sent once to load your
          courses and is never saved.
        </p>
        <form className="form" onSubmit={loadCourses}>
          <label className="field">
            Canvas access token
            <input
              type="password"
              value={token}
              onChange={(event) => setCanvasToken(event.target.value)}
              autoComplete="off"
              required
            />
          </label>
          <button className="button" type="submit" disabled={busy || !token}>
            Load my courses
          </button>
        </form>
      </section>

      {courses && (
        <section className="card">
          <h2>Choose courses</h2>
          {courses.length === 0 && <p className="muted">No active courses were found for this account.</p>}
          {courses.length > 0 && (
            <button type="button" className="button secondary" onClick={toggleAll} disabled={busy}>
              {allSelected ? "Clear selection" : "Select all"}
            </button>
          )}
          <ul className="list">
            {courses.map((course) => (
              <li key={course.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected.includes(course.id)}
                    onChange={() => toggle(course.id)}
                  />{" "}
                  {course.name}
                </label>
              </li>
            ))}
          </ul>
          <button className="button" type="button" disabled={busy || selected.length === 0} onClick={importSelected}>
            {busy ? "Importing…" : `Import ${selected.length} course(s)`}
          </button>
        </section>
      )}

      {result && (
        <section className="card">
          <h2>Import finished</h2>
          <p>
            {result.created} created, {result.updated} updated, {result.skipped.length} skipped.
          </p>
          <ul className="list">
            {result.courses.map((course) => (
              <li key={course.id}>
                <span>
                  {course.name}
                  <br />
                  <span className="muted">
                    {course.found === 0
                      ? "Canvas returned no assignments for this course."
                      : `${course.pending} pending of ${course.found} · ${course.created} created · ${course.updated} updated · ${course.skipped} skipped`}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {result.skipped.length > 0 && (
            <ul className="list">
              {result.skipped.map((item) => (
                <li key={item.canvas_id}>
                  <span>
                    {item.title} <span className="muted">· {item.reason}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          <ul className="list">
            {result.assignments.map((assignment) => (
              <li key={assignment.id}>
                <span>
                  {assignment.title} <span className="muted">· {assignment.course}</span>
                  <br />
                  <span className="muted">{formatDate(assignment.deadline)}</span>
                </span>
                <Link to={`/assignments/${assignment.id}`} className="button secondary">
                  Plan milestones
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
