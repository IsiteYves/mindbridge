import Link from "next/link";

export default function Home() {
  return (
    <section className="card">
      <h1>Plan your assignments, rubric by rubric</h1>
      <p className="muted">
        MindBridge turns each rubric criterion into a dated milestone, so you can see the work before the deadline.
      </p>
      <div className="form-row">
        <Link href="/import" className="button">
          Import from Canvas
        </Link>
        <Link href="/assignments" className="button secondary">
          My assignments
        </Link>
      </div>
    </section>
  );
}
