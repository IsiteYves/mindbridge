import type { ReactNode } from "react";

export type AuthVariant = "login" | "register" | "verify" | "forgot" | "reset";

type Props = {
  variant: AuthVariant;
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
};

// Each variant draws a different study-plan scene. Colors come from the theme tokens in index.css.
function AuthArt({ variant }: { variant: AuthVariant }) {
  return (
    <svg viewBox="0 0 480 400" role="img" aria-hidden="true" focusable="false">
      <circle className="art-soft" cx="240" cy="200" r="168" />
      <path className="art-line" d="M70 300 C 140 250, 170 330, 240 280 S 360 150, 420 190" />
      <rect className="art-ink" x="110" y="96" width="260" height="210" rx="18" />
      <rect className="art-accent" x="110" y="96" width="260" height="34" rx="18" />
      <rect className="art-text" x="136" y="150" width="120" height="10" rx="5" />
      <rect className="art-text" x="136" y="176" width="200" height="10" rx="5" />
      <rect className="art-text" x="136" y="202" width="160" height="10" rx="5" />
      <circle className="art-accent" cx="140" cy="256" r="11" />
      <rect className="art-text" x="162" y="251" width="130" height="10" rx="5" />
      <circle className="art-accent" cx="140" cy="284" r="11" />
      <rect className="art-text" x="162" y="279" width="96" height="10" rx="5" />
      {variant === "verify" && <rect className="art-accent" x="300" y="236" width="88" height="56" rx="10" />}
      {variant === "forgot" && <circle className="art-accent" cx="338" cy="250" r="30" />}
      {variant === "reset" && <rect className="art-accent" x="312" y="236" width="56" height="48" rx="10" />}
      {variant === "register" && <circle className="art-accent" cx="344" cy="112" r="22" />}
      {variant === "login" && <circle className="art-soft" cx="344" cy="112" r="22" />}
      <circle className="art-accent" cx="380" cy="80" r="8" />
      <circle className="art-soft" cx="80" cy="140" r="14" />
    </svg>
  );
}

export default function AuthLayout({ variant, title, subtitle, children }: Props) {
  return (
    <div className="auth-split">
      <section className="auth-form-panel">
        <div className="auth-form-inner">
          <h1>{title}</h1>
          {subtitle && <p className="muted">{subtitle}</p>}
          {children}
        </div>
      </section>
      <aside className="auth-art">
        <AuthArt variant={variant} />
      </aside>
    </div>
  );
}
