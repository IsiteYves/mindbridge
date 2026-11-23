import { Link, useLocation, useNavigate } from "react-router";

import { endSession } from "@/lib/session";

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/assignments", label: "My assignments" },
  { to: "/check-in", label: "Daily check-in" },
  { to: "/plan", label: "Study plan" },
  { to: "/import", label: "Import from Canvas" },
];

// Rendered only for signed-in users; logged-out visitors see PublicHeader instead.
export default function NavBar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  async function signOut() {
    await endSession();
    navigate("/login", { replace: true });
  }

  function isActive(to: string) {
    return pathname === to || pathname.startsWith(`${to}/`);
  }

  return (
    <aside className={`sidebar${open ? " open" : ""}`}>
      <Link to="/assignments" className="brand">
        <span className="brand-mark" aria-hidden="true">
          M
        </span>
        MindBridge
      </Link>

      <nav className="sidebar-nav" aria-label="Main navigation" onClick={onClose}>
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

      <div className="nudge-card">
        <p className="nudge-title">One step at a time.</p>
        <p className="muted">Small milestones make room for your bigger ambitions.</p>
      </div>

      <div className="sidebar-footer" onClick={onClose}>
        <Link
          to="/planning-guide"
          className={`nav-link${isActive("/planning-guide") ? " active" : ""}`}
          aria-current={isActive("/planning-guide") ? "page" : undefined}
        >
          Planning guide
        </Link>
        <Link
          to="/settings"
          className={`nav-link${isActive("/settings") ? " active" : ""}`}
          aria-current={isActive("/settings") ? "page" : undefined}
        >
          Settings
        </Link>
        <button type="button" className="nav-link" onClick={signOut}>
          Sign out
        </button>
      </div>
    </aside>
  );
}
