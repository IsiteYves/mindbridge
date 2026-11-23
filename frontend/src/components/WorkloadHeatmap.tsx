import { useEffect, useMemo, useState } from "react";

import { apiRequest, errorMessage } from "@/lib/api";

type WorkloadItem = { kind: "milestone" | "deadline"; id: number; assignment_id: number; title: string; course: string };
type WorkloadDay = { date: string; count: number; items: WorkloadItem[] };
type WorkloadResponse = { start: string; end: string; days: WorkloadDay[] };

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function startOfMonth(year: number, month: number): Date {
  return new Date(Date.UTC(year, month, 1));
}

function endOfMonth(year: number, month: number): Date {
  return new Date(Date.UTC(year, month + 1, 0));
}

// The calendar grid always starts on a Monday, padded with the trailing days
// of the previous month so every week is a full row.
function gridStart(monthStart: Date): Date {
  const weekday = (monthStart.getUTCDay() + 6) % 7; // 0 = Monday
  const start = new Date(monthStart);
  start.setUTCDate(start.getUTCDate() - weekday);
  return start;
}

function intensityClass(count: number): string {
  if (count === 0) return "";
  if (count === 1) return "heat-1";
  if (count <= 3) return "heat-2";
  if (count <= 5) return "heat-3";
  return "heat-4";
}

const MONTH_LABEL = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function WorkloadHeatmap({ assignmentId }: { assignmentId?: number } = {}) {
  const today = useMemo(() => new Date(), []);
  const [year, setYear] = useState(today.getUTCFullYear());
  const [month, setMonth] = useState(today.getUTCMonth());
  const [days, setDays] = useState<Record<string, WorkloadDay>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const monthStart = useMemo(() => startOfMonth(year, month), [year, month]);
  const monthEnd = useMemo(() => endOfMonth(year, month), [year, month]);
  const gridFirstDay = useMemo(() => gridStart(monthStart), [monthStart]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setLoading(true);
    const scope = assignmentId ? `&assignment_id=${assignmentId}` : "";
    apiRequest<WorkloadResponse>(
      `/schedule/workload?start=${toISODate(monthStart)}&end=${toISODate(monthEnd)}${scope}`,
    ).then(
      (response) => {
        if (cancelled) return;
        const byDate: Record<string, WorkloadDay> = {};
        for (const day of response.days) byDate[day.date] = day;
        setDays(byDate);
        setLoading(false);
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(errorMessage(err));
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [monthStart, monthEnd, assignmentId]);

  function changeMonth(delta: number) {
    const next = new Date(Date.UTC(year, month + delta, 1));
    setYear(next.getUTCFullYear());
    setMonth(next.getUTCMonth());
    setSelected(null);
  }

  const cells = useMemo(() => {
    const result: { date: string; inMonth: boolean }[] = [];
    const cursor = new Date(gridFirstDay);
    for (let i = 0; i < 42; i += 1) {
      result.push({ date: toISODate(cursor), inMonth: cursor.getUTCMonth() === month });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return result;
  }, [gridFirstDay, month]);

  const selectedDay = selected ? days[selected] : null;

  return (
    <div className="workload-heatmap">
      <div className="heatmap-header">
        <button type="button" className="button secondary" onClick={() => changeMonth(-1)} aria-label="Previous month">
          ←
        </button>
        <h3 className="mono-label">{MONTH_LABEL.format(monthStart)}</h3>
        <button type="button" className="button secondary" onClick={() => changeMonth(1)} aria-label="Next month">
          →
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="heatmap-weekdays">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label} className="muted small">
            {label}
          </span>
        ))}
      </div>

      <div
        className={`heatmap-grid${loading ? " loading" : ""}`}
        role="grid"
        aria-busy={loading}
        aria-label={`Workload for ${MONTH_LABEL.format(monthStart)}`}
      >
        {Array.from({ length: 6 }, (_, week) => (
          <div className="heatmap-row" role="row" key={week}>
            {cells.slice(week * 7, week * 7 + 7).map(({ date, inMonth }) => {
              const day = days[date];
              const count = day?.count ?? 0;
              return (
                <button
                  type="button"
                  key={date}
                  role="gridcell"
                  className={`heatmap-cell ${intensityClass(count)}${inMonth ? "" : " outside-month"}${
                    selected === date ? " selected" : ""
                  }`}
                  disabled={count === 0}
                  aria-label={`${date}, ${count} item${count === 1 ? "" : "s"} due`}
                  onClick={() => setSelected(date === selected ? null : date)}
                >
                  <span className="heatmap-date">{Number(date.slice(8, 10))}</span>
                  {count > 0 && (
                    <span className="heatmap-count">
                      {count} {count === 1 ? "item" : "items"}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {selectedDay && (
        <div className="heatmap-detail">
          <h4 className="mono-label">
            {selectedDay.date} · {selectedDay.count} item{selectedDay.count === 1 ? "" : "s"}
          </h4>
          <ul className="list">
            {selectedDay.items.map((item) => (
              <li key={`${item.kind}-${item.id}`}>
                <span>{item.title}</span>
                <span className="muted small">
                  {item.course} · {item.kind === "deadline" ? "assignment deadline" : "milestone"}
                </span>
              </li>
            ))}
          </ul>
          {selectedDay.count > selectedDay.items.length && (
            <p className="muted small">and {selectedDay.count - selectedDay.items.length} more that day.</p>
          )}
        </div>
      )}
    </div>
  );
}
