import { Link } from "react-router";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-grid">
        <div className="footer-brand">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              M
            </span>
            MindBridge
          </Link>
          <p className="muted">Turn every rubric into a plan you can actually finish.</p>
          <nav className="footer-links" aria-label="Footer">
            <Link to="/login">Sign in</Link>
            <Link to="/register">Create account</Link>
          </nav>
        </div>
      </div>
      <p className="footer-legal">
        © {new Date().getFullYear()} MindBridge. MindBridge does not diagnose or treat mental health.
      </p>
    </footer>
  );
}
