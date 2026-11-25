import { useCallback, useEffect, useState } from "react";

import { type AgentReview, type Milestone, apiRequest, errorMessage } from "@/lib/api";
import { notifyDataChanged, onDataChanged } from "@/lib/dataEvents";
import { toast } from "@/lib/toast";
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
  const [busy, setBusy] = useState(false);
  const [applyingId, setApplyingId] = useState<number | null>(null);
  const [applyingAll, setApplyingAll] = useState(false);

  const runReview = useCallback(async () => {
    setBusy(true);
    try {
      const result = await apiRequest<AgentReview>(`/assignments/${assignmentId}/milestones/review`, {
        method: "POST",
      });
      setReview(result);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [assignmentId]);

  const hasReview = review !== null;

  // After the first review, re-run it whenever data changes so the suggestions stay current.
  useEffect(() => {
    if (!hasReview) return;
    return onDataChanged(() => {
      void runReview();
    });
  }, [hasReview, runReview]);

  async function applySuggestedDate(milestoneId: number, newDate: string) {
    setApplyingId(milestoneId);
    try {
      const updated = await apiRequest<Milestone>(`/milestones/${milestoneId}`, {
        method: "PATCH",
        body: { target_date: newDate },
      });
      onMilestoneUpdated(updated);
      notifyDataChanged();
      toast.success("New target date applied.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setApplyingId(null);
    }
  }

  const applySuggestion = review?.replan_suggestion ?? null;
  const allApplied =
    applySuggestion !== null &&
    applySuggestion.milestone_ids.every(
      (id, index) => milestones.find((m) => m.id === id)?.target_date === applySuggestion.new_target_dates[index],
    );

  async function applyAll(suggestion: { milestone_ids: number[]; new_target_dates: string[] }) {
    setApplyingAll(true);
    try {
      for (let index = 0; index < suggestion.milestone_ids.length; index += 1) {
        const updated = await apiRequest<Milestone>(`/milestones/${suggestion.milestone_ids[index]}`, {
          method: "PATCH",
          body: { target_date: suggestion.new_target_dates[index] },
        });
        onMilestoneUpdated(updated);
      }
      toast.success("Suggested dates applied.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      notifyDataChanged();
      setApplyingAll(false);
    }
  }

  const titleFor = (milestoneId: number) => milestones.find((m) => m.id === milestoneId)?.title ?? `Milestone ${milestoneId}`;

  return (
    <div className="plan-review">
      <button aria-busy={busy} type="button" className="button secondary" onClick={runReview} disabled={busy}>
        {busy ? "Reviewing…" : review ? "Review again" : "Review my plan"}
      </button>


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
              <div className="card-title">
                <p className="mono-label">Suggested new dates</p>
                <button aria-busy={applyingAll}
                  type="button"
                  className="button compact"
                  disabled={applyingAll || allApplied}
                  onClick={() => applyAll(review.replan_suggestion!)}
                >
                  {allApplied ? "Applied" : applyingAll ? "Applying…" : "Apply all"}
                </button>
              </div>
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
                      <button aria-busy={applyingId === milestoneId}
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
