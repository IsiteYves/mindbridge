import { FormEvent, useState } from "react";

import PasswordRules from "@/components/PasswordRules";
import { type CurrentUser, apiRequest, errorMessage, publishAuthChange, setToken } from "@/lib/api";
import { unmetPasswordRules } from "@/lib/password";
import { toast } from "@/lib/toast";

export default function ProfileSettings({ user }: { user: CurrentUser }) {
  const [name, setName] = useState(user.name);
  const [nameBusy, setNameBusy] = useState(false);

  const [newEmail, setNewEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [emailCodeSent, setEmailCodeSent] = useState(false);
  const [emailCode, setEmailCode] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);

  const unmet = unmetPasswordRules(password);
  const passwordReady = currentPassword.length > 0 && unmet.length === 0 && confirm === password;

  async function saveName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNameBusy(true);
    try {
      await apiRequest<CurrentUser>("/auth/me", { method: "PATCH", body: { name } });
      publishAuthChange();
      toast.success("Name updated.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setNameBusy(false);
    }
  }

  async function requestEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailBusy(true);
    try {
      const { message } = await apiRequest<{ message: string }>("/auth/email/request-change", {
        method: "POST",
        body: { new_email: newEmail, current_password: emailPassword },
      });
      setEmailCodeSent(true);
      toast.success(message);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setEmailBusy(false);
    }
  }

  async function confirmEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailBusy(true);
    try {
      await apiRequest<CurrentUser>("/auth/email/confirm", { method: "POST", body: { code: emailCode } });
      publishAuthChange();
      setEmailCodeSent(false);
      setNewEmail("");
      setEmailPassword("");
      setEmailCode("");
      toast.success("Email updated.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setEmailBusy(false);
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordBusy(true);
    try {
      const { token } = await apiRequest<{ token: string }>("/auth/password", {
        method: "PATCH",
        body: { current_password: currentPassword, password, confirm_password: confirm },
      });
      setToken(token);
      setCurrentPassword("");
      setPassword("");
      setConfirm("");
      toast.success("Password updated. Other devices have been signed out.");
    } catch (err) {
      toast.error(errorMessage(err));
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
          <div className="update-row">
            <button className="button compact" type="submit" disabled={nameBusy || name.trim() === user.name}>
              {nameBusy ? "Updating…" : "Update"}
            </button>
          </div>
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
            <div className="update-row">
              <button className="button compact" type="submit" disabled={emailBusy || !newEmail || !emailPassword}>
                {emailBusy ? "Sending…" : "Send code"}
              </button>
            </div>
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
            <div className="update-row">
              <button className="button compact" type="submit" disabled={emailBusy || emailCode.length !== 6}>
                {emailBusy ? "Confirming…" : "Update"}
              </button>
            </div>
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
          <div className="update-row">
            <button className="button compact" type="submit" disabled={passwordBusy || !passwordReady}>
              {passwordBusy ? "Updating…" : "Update"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
