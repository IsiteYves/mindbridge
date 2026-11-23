import type { Milestone, Status } from "@/lib/api";
import { daysLeftLabel, daysRemaining, encouragement } from "@/lib/progress";

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function placement(fraction: number): string {
  return `${Math.min(94, Math.max(6, fraction * 100))}%`;
}

function shortDate(date: Date): string {
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(date).toUpperCase();
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
  const doneCount = milestones.filter((m) => m.status === "done").length;
  const daysLeft = daysRemaining(deadlineDate, now);
  const cheer = encouragement(doneCount, milestones.length, daysLeft);

  const earliestMilestone = ordered[0] ? new Date(ordered[0].target_date) : null;
  const start = earliestMilestone && earliestMilestone < now ? earliestMilestone : now;
  const span = deadlineDate.getTime() - start.getTime();

  if (span <= 0) {
    return <p className="muted">{daysLeftLabel(deadlineDate, now)}. Edit your plan below.</p>;
  }

  const fraction = (iso: string) => clamp01((new Date(iso).getTime() - start.getTime()) / span);
  const todayFraction = clamp01((now.getTime() - start.getTime()) / span);

  return (
    <div className="milestone-rail">
      <div className="rail-header">
        <span className="mono-label">
          {doneCount} of {milestones.length} complete
        </span>
        <span className="days-left-badge">{daysLeftLabel(deadlineDate, now)}</span>
      </div>
      <p className="rail-cheer">
        <span aria-hidden="true">{cheer.emoji}</span> {cheer.text}
      </p>

      <div className="rail-track" role="img" aria-label={`Timeline from ${shortDate(start)} to ${shortDate(deadlineDate)}`}>
        <div className="rail-line" />
        <div className="rail-today-marker" style={{ left: placement(todayFraction) }}>
          <span className="mono-label">TODAY</span>
        </div>
        <div className="rail-due-marker">
          <span className="mono-label">
            DUE · {shortDate(deadlineDate)} {deadlineDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>

        {ordered.map((milestone) => (
          <div
            key={milestone.id}
            className={`rail-node rail-node-${milestone.status}`}
            style={{ left: placement(fraction(milestone.target_date)) }}
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
