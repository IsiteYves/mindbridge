import { BookOpen, CalendarDays, ClipboardList, CloudDownload, HeartPulse, LayoutDashboard, LogOut, MessageSquare, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router";

import { endSession } from "@/lib/session";

const LINKS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assignments", label: "My assignments", icon: ClipboardList },
  { to: "/check-in", label: "Daily check-in", icon: HeartPulse },
  { to: "/plan", label: "Study plan", icon: CalendarDays },
  { to: "/import", label: "Import from Canvas", icon: CloudDownload },
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

      <nav className="sidebar-nav" aria-label="Main navigation">
        {LINKS.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={`nav-link${isActive(link.to) ? " active" : ""}`}
            aria-current={isActive(link.to) ? "page" : undefined}
            onClick={onClose}
          >
            <link.icon size={18} strokeWidth={1.75} aria-hidden="true" />
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
          onClick={onClose}
        >
          <BookOpen size={18} strokeWidth={1.75} aria-hidden="true" />
          Planning guide
        </Link>
        <Link
          to="/feedback"
          className={`nav-link${isActive("/feedback") ? " active" : ""}`}
          aria-current={isActive("/feedback") ? "page" : undefined}
          onClick={onClose}
        >
          <MessageSquare size={18} strokeWidth={1.75} aria-hidden="true" />
          Feedback
        </Link>
        <Link
          to="/settings"
          className={`nav-link${isActive("/settings") ? " active" : ""}`}
          aria-current={isActive("/settings") ? "page" : undefined}
          onClick={onClose}
        >
          <Settings size={18} strokeWidth={1.75} aria-hidden="true" />
          Settings
        </Link>
        <button
          type="button"
          className="nav-link"
          onClick={() => {
            onClose();
            void signOut();
          }}
        >
          <LogOut size={18} strokeWidth={1.75} aria-hidden="true" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
