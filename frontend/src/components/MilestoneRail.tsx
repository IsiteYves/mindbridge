import type { Milestone, Status } from "@/lib/api";
import { daysLeftLabel, daysRemaining, encouragement } from "@/lib/progress";

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
  const cheer = encouragement(doneCount, milestones.length, daysRemaining(deadlineDate, now));
  // The Today marker goes before the first milestone that is still in the future.
  const todayIndex = ordered.findIndex((m) => new Date(m.target_date).getTime() > now.getTime());
  const todayAt = todayIndex === -1 ? ordered.length : todayIndex;

  const todayRow = (
    <li key="today" className="rail-step rail-today">
      <span className="rail-dot" aria-hidden="true" />
      <span className="mono-label">Today · {shortDate(now)}</span>
    </li>
  );

  const milestoneRows = ordered.flatMap((milestone, index) => {
    const row = (
      <li key={milestone.id} className={`rail-step rail-node-${milestone.status}`}>
        <span className="rail-dot" aria-hidden="true">
          {statusGlyph(milestone.status)}
        </span>
        <div className="rail-node-text">
          <span className="rail-node-date mono-label">{shortDate(new Date(milestone.target_date))}</span>
          <span className="rail-node-label">{milestone.title}</span>
        </div>
      </li>
    );
    return index === todayAt ? [todayRow, row] : [row];
  });
  if (todayAt === ordered.length) milestoneRows.push(todayRow);

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

      <ol className="rail-steps" aria-label="Milestones in date order">
        {milestoneRows}
        <li className="rail-step rail-due">
          <span className="rail-dot" aria-hidden="true" />
          <span className="mono-label">
            Due · {shortDate(deadlineDate)} {deadlineDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
          </span>
        </li>
      </ol>
    </div>
  );
}
