import { FormEvent, useState } from "react";

import PasswordRules from "@/components/PasswordRules";
import { type CurrentUser, apiRequest, errorMessage, publishAuthChange, setToken } from "@/lib/api";
import { unmetPasswordRules } from "@/lib/password";

export default function ProfileSettings({ user }: { user: CurrentUser }) {
  const [name, setName] = useState(user.name);
  const [nameBusy, setNameBusy] = useState(false);
  const [nameNotice, setNameNotice] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [emailCodeSent, setEmailCodeSent] = useState(false);
  const [emailCode, setEmailCode] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailNotice, setEmailNotice] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const unmet = unmetPasswordRules(password);
  const passwordReady = currentPassword.length > 0 && unmet.length === 0 && confirm === password;

  async function saveName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNameBusy(true);
    setNameError(null);
    setNameNotice(null);
    try {
      await apiRequest<CurrentUser>("/auth/me", { method: "PATCH", body: { name } });
      publishAuthChange();
      setNameNotice("Name updated.");
    } catch (err) {
      setNameError(errorMessage(err));
    } finally {
      setNameBusy(false);
    }
  }

  async function requestEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailBusy(true);
    setEmailError(null);
    setEmailNotice(null);
    try {
      const { message } = await apiRequest<{ message: string }>("/auth/email/request-change", {
        method: "POST",
        body: { new_email: newEmail, current_password: emailPassword },
      });
      setEmailCodeSent(true);
      setEmailNotice(message);
    } catch (err) {
      setEmailError(errorMessage(err));
    } finally {
      setEmailBusy(false);
    }
  }

  async function confirmEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailBusy(true);
    setEmailError(null);
    try {
      await apiRequest<CurrentUser>("/auth/email/confirm", { method: "POST", body: { code: emailCode } });
      publishAuthChange();
      setEmailCodeSent(false);
      setNewEmail("");
      setEmailPassword("");
      setEmailCode("");
      setEmailNotice("Email updated.");
    } catch (err) {
      setEmailError(errorMessage(err));
    } finally {
      setEmailBusy(false);
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordBusy(true);
    setPasswordError(null);
    setPasswordNotice(null);
    try {
      const { token } = await apiRequest<{ token: string }>("/auth/password", {
        method: "PATCH",
        body: { current_password: currentPassword, password, confirm_password: confirm },
      });
      setToken(token);
      setCurrentPassword("");
      setPassword("");
      setConfirm("");
      setPasswordNotice("Password updated. Other devices have been signed out.");
    } catch (err) {
      setPasswordError(errorMessage(err));
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className="profile-settings">
      <section className="settings-section">
        <h3>Name</h3>
        <form className="form" onSubmit={saveName}>
          <label className="field">
            Full name
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required />
          </label>
          {nameNotice && <p className="notice">{nameNotice}</p>}
          {nameError && <p className="error">{nameError}</p>}
          <button className="button" type="submit" disabled={nameBusy || name.trim() === user.name}>
            {nameBusy ? "Updating…" : "Update name"}
          </button>
        </form>
      </section>

      <section className="settings-section">
        <h3>Email</h3>
        <p className="muted small">Current: {user.email}</p>
        {!emailCodeSent ? (
          <form className="form" onSubmit={requestEmailChange}>
            <label className="field">
              New email
              <input type="email" value={newEmail} onChange={(event) => setNewEmail(event.target.value)} required />
            </label>
            <label className="field">
              Current password
              <input
                type="password"
                autoComplete="current-password"
                value={emailPassword}
                onChange={(event) => setEmailPassword(event.target.value)}
                required
              />
            </label>
            {emailNotice && <p className="notice">{emailNotice}</p>}
            {emailError && <p className="error">{emailError}</p>}
            <button className="button" type="submit" disabled={emailBusy || !newEmail || !emailPassword}>
              {emailBusy ? "Sending…" : "Send code to new email"}
            </button>
          </form>
        ) : (
          <form className="form" onSubmit={confirmEmailChange}>
            <label className="field">
              Code sent to {newEmail}
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={emailCode}
                onChange={(event) => setEmailCode(event.target.value.replace(/\D/g, ""))}
                required
              />
            </label>
            {emailError && <p className="error">{emailError}</p>}
            <button className="button" type="submit" disabled={emailBusy || emailCode.length !== 6}>
              {emailBusy ? "Confirming…" : "Update email"}
            </button>
          </form>
        )}
      </section>

      <section className="settings-section">
        <h3>Password</h3>
        <form className="form" onSubmit={changePassword}>
          <label className="field">
            Current password
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
            />
          </label>
          <label className="field">
            New password
            <input
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <PasswordRules password={password} />
          <label className="field">
            Confirm new password
            <input
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              required
            />
          </label>
          {passwordNotice && <p className="notice">{passwordNotice}</p>}
          {passwordError && <p className="error">{passwordError}</p>}
          <button className="button" type="submit" disabled={passwordBusy || !passwordReady}>
            {passwordBusy ? "Updating…" : "Update password"}
          </button>
        </form>
      </section>
    </div>
  );
}
