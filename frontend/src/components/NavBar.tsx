import { Link, useLocation, useNavigate } from "react-router";

import { clearToken, getToken } from "@/lib/api";

const LINKS = [
  { to: "/", label: "Overview" },
  { to: "/assignments", label: "Assignments" },
  { to: "/import", label: "Import from Canvas" },
];

export default function NavBar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const signedIn = getToken() !== null;

  function signOut() {
    clearToken();
    navigate("/login");
  }

  function isActive(to: string) {
    if (to === "/") return pathname === "/";
    return pathname === to || pathname.startsWith(`${to}/`);
  }

  return (
    <aside className="sidebar">
      <Link to="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          M
        </span>
        MindBridge
      </Link>

      <div>
        <p className="nav-section-title">Workspace</p>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`nav-link${isActive(link.to) ? " active" : ""}`}
              aria-current={isActive(link.to) ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="sidebar-footer">
        {signedIn ? (
          <button type="button" className="link-button" onClick={signOut}>
            Sign out
          </button>
        ) : (
          <Link to="/login" className="nav-link">
            Sign in
          </Link>
        )}
      </div>
    </aside>
  );
}
