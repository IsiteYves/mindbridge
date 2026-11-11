import { PASSWORD_RULES } from "@/lib/password";

export default function PasswordRules({ password }: { password: string }) {
  return (
    <ul className="rules" aria-label="Password requirements">
      {PASSWORD_RULES.map((rule) => {
        const met = rule.test(password);
        return (
          <li key={rule.label} className={met ? "met" : undefined}>
            {met ? "✓ " : "· "}
            {rule.label}
          </li>
        );
      })}
    </ul>
  );
}
