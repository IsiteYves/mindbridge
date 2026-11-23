import { useEffect, useState } from "react";

import { toast } from "@/lib/toast";
import {
  type NotificationItem,
  type ReminderOffset,
  type ReminderPreference,
  REMINDER_OFFSETS,
  apiRequest,
  errorMessage,
} from "@/lib/api";

const OFFSET_LABEL: Record<ReminderOffset, string> = {
  5: "5 days before",
  2: "2 days before",
  1: "1 day before",
  0: "On the due date",
};

const KIND_LABEL: Record<string, string> = {
  deadline: "Deadline",
  milestone: "Milestone",
  overdue: "Overdue",
  new_item: "New Item",
};

function InboxGroup({
  title,
  items,
  onDismiss,
}: {
  title: string;
  items: NotificationItem[];
  onDismiss: (id: number) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="inbox-group">
      <h4 className="mono-label">{title}</h4>
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>
            <span>{KIND_LABEL[item.kind] ?? item.kind}</span>
            <button type="button" className="button secondary compact" onClick={() => onDismiss(item.id)}>
              Dismiss
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function NotificationSettings() {
  const [preferences, setPreferences] = useState<ReminderPreference[] | null>(null);
  const [draft, setDraft] = useState<Partial<Record<ReminderOffset, boolean>>>({});
  const [inbox, setInbox] = useState<NotificationItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiRequest<ReminderPreference[]>("/notifications/preferences"),
      apiRequest<NotificationItem[]>("/notifications"),
    ]).then(
      ([loadedPreferences, loadedInbox]) => {
        if (cancelled) return;
        setPreferences(loadedPreferences);
        setInbox(loadedInbox);
      },
      (err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const savedFor = (offset: ReminderOffset) =>
    preferences?.find((preference) => preference.offset_days === offset)?.enabled ?? true;
  const enabledFor = (offset: ReminderOffset) => draft[offset] ?? savedFor(offset);
  const dirty = REMINDER_OFFSETS.some((offset) => draft[offset] !== undefined && draft[offset] !== savedFor(offset));

  async function saveChanges() {
    setSaving(true);
    try {
      const updated = await apiRequest<ReminderPreference[]>("/notifications/preferences", {
        method: "PUT",
        body: { preferences: REMINDER_OFFSETS.map((offset) => ({ offset_days: offset, enabled: enabledFor(offset) })) },
      });
      setPreferences(updated);
      setDraft({});
      toast.success("Reminder settings updated.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function dismiss(id: number) {
    try {
      await apiRequest(`/notifications/${id}/dismiss`, { method: "POST" });
      setInbox((current) => (current ?? []).filter((item) => item.id !== id));
    } catch (err) {
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="notification-settings">
      {error && <p className="error">{error}</p>}

      <div className="reminder-offsets">
        {REMINDER_OFFSETS.map((offset) => (
          <label className="reminder-offset-row" key={offset}>
            <span>{OFFSET_LABEL[offset]}</span>
            <input
              type="checkbox"
              checked={enabledFor(offset)}
              disabled={preferences === null || saving}
              onChange={(event) => setDraft((current) => ({ ...current, [offset]: event.target.checked }))}
            />
          </label>
        ))}
      </div>
      <div className="update-row">
        <button className="button compact" type="button" disabled={!dirty || saving} onClick={saveChanges}>
          {saving ? "Updating…" : "Update"}
        </button>
      </div>
      <p className="muted small">
        You'll also always hear about anything overdue, once a day until it's done, and about anything new a Canvas
        import adds to your plan. Those two aren't optional.
      </p>

      <div className="notification-inbox">
        <h3>Inbox</h3>
        {inbox === null && !error && <p className="muted">Loading…</p>}
        {inbox && inbox.length === 0 && <p className="empty-state">Nothing to show yet.</p>}
        {inbox && inbox.length > 0 && (
          <>
            <InboxGroup title="Reminders" items={inbox.filter((item) => item.kind !== "new_item")} onDismiss={dismiss} />
            <InboxGroup title="Updates" items={inbox.filter((item) => item.kind === "new_item")} onDismiss={dismiss} />
          </>
        )}
      </div>
    </div>
  );
}
