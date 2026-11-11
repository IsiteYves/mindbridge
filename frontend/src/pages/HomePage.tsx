import { Link } from "react-router";

const STEPS = [
  {
    title: "Connect your Canvas courses",
    body: "Paste a personal access token once. MindBridge loads your active courses and imports each assignment with its due date.",
  },
  {
    title: "Split each rubric into milestones",
    body: "Every rubric criterion becomes a dated milestone, spread evenly between today and the deadline, so the work has a shape.",
  },
  {
    title: "Track progress and adjust",
    body: "Edit milestone titles and dates, mark work as in progress or done, and regenerate the plan when the criteria change.",
  },
];

const BENEFITS = [
  {
    title: "See the real work",
    body: "You get a checkpoint for each criterion, so you know what to do next instead of staring at a single due date.",
  },
  {
    title: "Start earlier, without the guilt",
    body: "Milestones land well before the deadline. Finishing one early is a win you can see, not a debt you carry.",
  },
  {
    title: "Your token stays yours",
    body: "The Canvas token is used for the import and is never saved. Your account only stores the assignments and milestones.",
  },
];

export default function HomePage() {
  return (
    <div className="landing">
      <section className="hero">
        <h1>Turn every rubric into a plan you can actually finish.</h1>
        <p className="hero-lead">
          MindBridge imports your Canvas assignments and breaks each rubric criterion into a dated milestone, so big
          projects stop feeling like a last-night scramble.
        </p>
        <div className="hero-actions">
          <Link to="/register" className="button">
            Create your account
          </Link>
          <Link to="/login" className="button secondary">
            Sign in
          </Link>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <h2>How it works</h2>
          <p>Three steps from a pile of deadlines to a plan with dates on it.</p>
        </div>
        <div className="step-grid">
          {STEPS.map((step, index) => (
            <article className="step-card" key={step.title}>
              <span className="step-number" aria-hidden="true">
                {index + 1}
              </span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <div className="section-heading">
          <h2>Built for how students actually work</h2>
        </div>
        <div className="benefit-grid">
          {BENEFITS.map((benefit) => (
            <article className="benefit-card" key={benefit.title}>
              <h3>{benefit.title}</h3>
              <p>{benefit.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="closing-cta">
        <div>
          <h2>Start with your next deadline</h2>
          <p className="muted">Create an account, verify your email, then import the course you are working on.</p>
        </div>
        <Link to="/register" className="button">
          Create your account
        </Link>
      </section>
    </div>
  );
}
