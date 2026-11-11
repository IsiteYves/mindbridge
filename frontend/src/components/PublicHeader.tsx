import { Link } from "react-router";

export default function PublicHeader() {
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          M
        </span>
        MindBridge
      </Link>
      <nav className="topbar-actions" aria-label="Account">
        <Link to="/login" className="button secondary">
          Sign in
        </Link>
        <Link to="/register" className="button">
          Create account
        </Link>
      </nav>
    </header>
  );
}
