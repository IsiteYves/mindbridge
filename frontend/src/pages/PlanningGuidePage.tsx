export default function PlanningGuidePage() {
  return (
    <div className="planning-guide">
      <div className="page-header">
        <div className="stack">
          <h1>Planning guide</h1>
          <p className="muted">A clear route through the work that matters.</p>
        </div>
      </div>

      <section className="card">
        <h2>Break the assignment down before you start</h2>
        <p>
          A rubric lists what gets graded, not the order you should work in. Read it once end to end, then turn
          each criterion into a milestone with its own target date. Four criteria rarely deserve four equal days —
          a criterion worth 30% of the grade deserves more of your working time than one worth 10%.
        </p>
      </section>

      <section className="card">
        <h2>Leave a day before the deadline</h2>
        <p>
          Your last milestone should land at least a day before the assignment is due. That gap is for reading your
          own work back, not for finishing it. If your plan's final target is the same day as the deadline, move it
          earlier.
        </p>
      </section>

      <section className="card">
        <h2>Reorder freely, keep your dates honest</h2>
        <p>
          You can reorder your milestones at any time to change how your plan reads, without changing when the
          work is due. If a target date stops being realistic, edit the date itself rather than leaving it to
          slip — a plan you trust is one you'll actually follow.
        </p>
      </section>

      <section className="card">
        <h2>Use focus sessions for the milestone in front of you</h2>
        <p>
          Pick one milestone, start a focus session, and work only on that until the timer ends. A short break
          after each session is part of the plan, not a distraction from it.
        </p>
      </section>
    </div>
  );
}
