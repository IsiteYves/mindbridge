import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <section className="card">
      <h1>Page not found</h1>
      <p className="muted">The page you were looking for does not exist or has moved.</p>
      <div className="form-row">
        <Link to="/" className="button">
          Go to home
        </Link>
      </div>
    </section>
  );
}
