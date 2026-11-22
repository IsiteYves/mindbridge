import { useState } from "react";

import { type AgentReview, type Milestone, apiRequest, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/dates";

export default function PlanReview({
  assignmentId,
  milestones,
  onMilestoneUpdated,
}: {
  assignmentId: string;
  milestones: Milestone[];
  onMilestoneUpdated: (milestone: Milestone) => void;
}) {
  const [review, setReview] = useState<AgentReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applyingId, setApplyingId] = useState<number | null>(null);

  async function runReview() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<AgentReview>(`/assignments/${assignmentId}/milestones/review`, {
        method: "POST",
      });
      setReview(result);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function applySuggestedDate(milestoneId: number, newDate: string) {
    setApplyingId(milestoneId);
    setError(null);
    try {
      const updated = await apiRequest<Milestone>(`/milestones/${milestoneId}`, {
        method: "PATCH",
        body: { target_date: newDate },
      });
      onMilestoneUpdated(updated);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setApplyingId(null);
    }
  }

  const titleFor = (milestoneId: number) => milestones.find((m) => m.id === milestoneId)?.title ?? `Milestone ${milestoneId}`;

  return (
    <div className="plan-review">
      <button type="button" className="button secondary" onClick={runReview} disabled={busy}>
        {busy ? "Reviewing…" : review ? "Review again" : "Review my plan"}
      </button>

      {error && <p className="error">{error}</p>}

      {review && (
        <div className="review-result">
          <p className="mono-label">Reviewed {formatDate(review.generated_at)}</p>
          <p>{review.summary}</p>

          {review.findings.length > 0 && (
            <ul className="review-findings">
              {review.findings.map((finding, index) => (
                <li key={index} className={`finding finding-${finding.severity}`}>
                  {finding.milestone_id && <strong>{titleFor(finding.milestone_id)}: </strong>}
                  {finding.message}
                </li>
              ))}
            </ul>
          )}

          {review.replan_suggestion && (
            <div className="replan-suggestion">
              <p className="mono-label">Suggested new dates</p>
              <p className="muted small">Nothing here changes until you apply it.</p>
              <ul className="list">
                {review.replan_suggestion.milestone_ids.map((milestoneId, index) => {
                  const newDate = review.replan_suggestion!.new_target_dates[index];
                  const current = milestones.find((m) => m.id === milestoneId);
                  const alreadyApplied = current?.target_date === newDate;
                  return (
                    <li key={milestoneId}>
                      <span>{titleFor(milestoneId)}</span>
                      <span className="muted small">→ {formatDate(newDate)}</span>
                      <button
                        type="button"
                        className="button secondary"
                        disabled={applyingId === milestoneId || alreadyApplied}
                        onClick={() => applySuggestedDate(milestoneId, newDate)}
                      >
                        {alreadyApplied ? "Applied" : applyingId === milestoneId ? "Applying…" : "Apply"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
