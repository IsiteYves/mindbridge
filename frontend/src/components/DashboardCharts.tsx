import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DashboardSummary } from "@/lib/api";

const COLORS = {
  notStarted: "#64748b",
  inProgress: "#b45309",
  closed: "#15803d",
  deadlines: "#0f766e",
  focus: "#2dd4bf",
};

const DAY = new Intl.DateTimeFormat("en-GB", { weekday: "short" });
const SHORT_DATE = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" });

function dayOf(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function StatusChart({ counts }: { counts: DashboardSummary["counts"] }) {
  const data = [
    { name: "Not started", value: counts.pending - counts.in_progress, color: COLORS.notStarted },
    { name: "In progress", value: counts.in_progress, color: COLORS.inProgress },
    { name: "Closed", value: counts.closed, color: COLORS.closed },
  ].filter((slice) => slice.value > 0);

  return (
    <article className="card chart-card">
      <h3 className="mono-label">Status</h3>
      {data.length === 0 ? (
        <p className="empty-state">No assignments yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
              {data.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </article>
  );
}

export function DeadlinesChart({ deadlines }: { deadlines: DashboardSummary["deadlines"] }) {
  const data = deadlines.map((week) => ({
    label: `From ${SHORT_DATE.format(dayOf(week.week_start))}`,
    count: week.count,
  }));
  const total = data.reduce((sum, week) => sum + week.count, 0);

  return (
    <article className="card chart-card">
      <h3 className="mono-label">Deadlines, next 4 weeks</h3>
      {total === 0 ? (
        <p className="empty-state">Nothing due in the next four weeks.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" name="Assignments due" fill={COLORS.deadlines} radius={[6, 6, 0, 0]} />
            <Legend />
          </BarChart>
        </ResponsiveContainer>
      )}
    </article>
  );
}

export function FocusChart({ focus }: { focus: DashboardSummary["focus"] }) {
  const data = focus.map((day) => ({ label: DAY.format(dayOf(day.date)), minutes: day.minutes }));
  const total = data.reduce((sum, day) => sum + day.minutes, 0);

  return (
    <article className="card chart-card">
      <h3 className="mono-label">Focus minutes, last 7 days</h3>
      {total === 0 ? (
        <p className="empty-state">No focus time yet this week.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="minutes" name="Focus minutes" fill={COLORS.focus} radius={[6, 6, 0, 0]} />
            <Legend />
          </BarChart>
        </ResponsiveContainer>
      )}
    </article>
  );
}
