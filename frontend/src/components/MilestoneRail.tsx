import type { Milestone, Status } from "@/lib/api";

const DAY_MS = 24 * 60 * 60 * 1000;

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function shortDate(date: Date): string {
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(date).toUpperCase();
}

function daysLeftLabel(deadline: Date, now: Date): string {
  const days = Math.ceil((deadline.getTime() - now.getTime()) / DAY_MS);
  if (days < 0) return "Overdue";
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

function statusGlyph(status: Status): string {
  if (status === "done") return "✓";
  if (status === "in_progress") return "◐";
  return "";
}

export default function MilestoneRail({ milestones, deadline }: { milestones: Milestone[]; deadline: string | null }) {
  if (!deadline) {
    return <p className="muted">Set a deadline to see this assignment's timeline.</p>;
  }

  const deadlineDate = new Date(deadline);
  const now = new Date();
  const ordered = [...milestones].sort((a, b) => a.target_date.localeCompare(b.target_date));

  const earliestMilestone = ordered[0] ? new Date(ordered[0].target_date) : null;
  const start = earliestMilestone && earliestMilestone < now ? earliestMilestone : now;
  const span = deadlineDate.getTime() - start.getTime();

  if (span <= 0) {
    return <p className="muted">{daysLeftLabel(deadlineDate, now)}. Edit your plan below.</p>;
  }

  const fraction = (iso: string) => clamp01((new Date(iso).getTime() - start.getTime()) / span);
  const todayFraction = clamp01((now.getTime() - start.getTime()) / span);
  const doneCount = milestones.filter((m) => m.status === "done").length;

  return (
    <div className="milestone-rail">
      <div className="rail-header">
        <span className="mono-label">
          {doneCount} of {milestones.length} complete
        </span>
        <span className="days-left-badge">{daysLeftLabel(deadlineDate, now)}</span>
      </div>

      <div className="rail-track" role="img" aria-label={`Timeline from ${shortDate(start)} to ${shortDate(deadlineDate)}`}>
        <div className="rail-line" />
        <div className="rail-today-marker" style={{ left: `${todayFraction * 100}%` }}>
          <span className="mono-label">TODAY</span>
        </div>
        <div className="rail-due-marker" style={{ left: "100%" }}>
          <span className="mono-label">
            DUE · {shortDate(deadlineDate)} {deadlineDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>

        {ordered.map((milestone) => (
          <div
            key={milestone.id}
            className={`rail-node rail-node-${milestone.status}`}
            style={{ left: `${fraction(milestone.target_date) * 100}%` }}
          >
            <span className="rail-node-dot" aria-hidden="true">
              {statusGlyph(milestone.status)}
            </span>
            <span className="rail-node-date mono-label">{shortDate(new Date(milestone.target_date))}</span>
            <span className="rail-node-label">{milestone.title}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
