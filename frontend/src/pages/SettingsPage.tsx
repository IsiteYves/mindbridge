import { useState } from "react";
import { useSearchParams } from "react-router";

import CanvasIntegration from "@/components/CanvasIntegration";
import ProfileSettings from "@/components/ProfileSettings";
import NotificationSettings from "@/components/NotificationSettings";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { useTheme } from "@/lib/useTheme";

type TabId = "profile" | "notifications" | "integrations";

const TABS: { id: TabId; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "notifications", label: "Notifications" },
  { id: "integrations", label: "Integrations" },
];

// Older links use ?section=integration; map them to the current tab id.
const SECTION_ALIASES: Record<string, TabId> = { integration: "integrations" };

function initialTab(requested: string | null): TabId {
  const resolved = requested ? (SECTION_ALIASES[requested] ?? requested) : null;
  return TABS.some((tab) => tab.id === resolved) ? (resolved as TabId) : "profile";
}

export default function SettingsPage() {
  const [params] = useSearchParams();
  const [active, setActive] = useState<TabId>(() => initialTab(params.get("section")));
  const user = useCurrentUser();
  const [theme, toggleTheme] = useTheme();

  return (
    <div className="settings-page">
      <div className="page-header">
        <div className="stack">
          <h1>Settings</h1>
          <p className="muted">Your account, your reminders, your connections.</p>
        </div>
      </div>

      <div className="card">
        <div className="settings-tabs" role="tablist" aria-label="Settings sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active === tab.id}
              className={`settings-tab${active === tab.id ? " active" : ""}`}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {active === "profile" && (
          <div className="settings-panel" role="tabpanel">
            {user ? <ProfileSettings user={user} /> : <p className="muted">Loading your profile…</p>}

            <div className="appearance-row">
              <div>
                <p className="field-label">Appearance</p>
                <p className="muted small">The same switch also lives in the top bar, for a quicker change.</p>
              </div>
              <button type="button" className="button secondary" onClick={toggleTheme}>
                {theme === "dark" ? "Switch to light" : "Switch to dark"}
              </button>
            </div>
          </div>
        )}

        {active === "notifications" && (
          <div className="settings-panel" role="tabpanel">
            <NotificationSettings />
          </div>
        )}

        {active === "integrations" && (
          <div className="settings-panel" role="tabpanel">
            <CanvasIntegration />
          </div>
        )}
      </div>
    </div>
  );
}
