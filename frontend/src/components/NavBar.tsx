import { Link, useLocation } from "react-router";

// "Home" is deliberately not listed yet: for a signed-in user "/" redirects
// straight to "/assignments" today (see App.tsx), so a separate Home entry
// would either duplicate this one or point at a page that doesn't exist. A
// real dashboard/overview surface is planned (see the assignment planner
// work later this week) and gets its own nav entry once it exists.
const LINKS = [
  { to: "/assignments", label: "My assignments" },
  { to: "/check-in", label: "Daily check-in" },
  { to: "/plan", label: "Study plan" },
  { to: "/import", label: "Import from Canvas" },
];

// Rendered only for signed-in users; logged-out visitors see PublicHeader instead.
export default function NavBar() {
  const { pathname } = useLocation();

  function isActive(to: string) {
    return pathname === to || pathname.startsWith(`${to}/`);
  }

  return (
    <aside className="sidebar">
      <Link to="/assignments" className="brand">
        <span className="brand-mark" aria-hidden="true">
          M
        </span>
        MindBridge
      </Link>

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

      <div className="nudge-card">
        <p className="nudge-title">One step at a time.</p>
        <p className="muted">Small milestones make room for your bigger ambitions.</p>
      </div>

      <div className="sidebar-footer">
        <Link
          to="/planning-guide"
          className={`nav-link${isActive("/planning-guide") ? " active" : ""}`}
          aria-current={isActive("/planning-guide") ? "page" : undefined}
        >
          Planning guide
        </Link>
      </div>
    </aside>
  );
}
