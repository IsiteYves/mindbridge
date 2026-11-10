import { Link } from "react-router";

export default function HomePage() {
  return (
    <section className="card">
      <h1>Plan your assignments, rubric by rubric</h1>
      <p className="muted">
        MindBridge turns each rubric criterion into a dated milestone, so you can see the work before the deadline.
      </p>
      <div className="form-row">
        <Link to="/import" className="button">
          Import from Canvas
        </Link>
        <Link to="/assignments" className="button secondary">
          My assignments
        </Link>
      </div>
    </section>
  );
}
