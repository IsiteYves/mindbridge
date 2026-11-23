import { useEffect, useState } from "react";

import DailyGoalCard from "@/components/DailyGoalCard";
import { DeadlinesChart, FocusChart, StatusChart } from "@/components/DashboardCharts";
import FocusTimerCard from "@/components/FocusTimerCard";
import { type DashboardSummary, apiRequest, errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiRequest<DashboardSummary>("/dashboard/summary").then(
      (loaded) => {
        if (!cancelled) setSummary(loaded);
      },
      (err: unknown) => toast.error(errorMessage(err)),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <header className="page-header">
        <div className="stack">
          <h1>Dashboard</h1>
        </div>
      </header>

      <section className="dashboard-row" aria-label="Today">
        <DailyGoalCard />
        <FocusTimerCard />
      </section>

      {summary === null ? (
        <p className="muted">Loading…</p>
      ) : (
        <section className="chart-grid" aria-label="Charts">
          <StatusChart counts={summary.counts} />
          <DeadlinesChart deadlines={summary.deadlines} />
          <FocusChart focus={summary.focus} />
        </section>
      )}
    </>
  );
}
