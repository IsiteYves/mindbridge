import { type ReactElement, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router";

import AppTopbar from "@/components/AppTopbar";
import NavBar from "@/components/NavBar";
import PublicHeader from "@/components/PublicHeader";
import SiteFooter from "@/components/SiteFooter";
import ToastHost from "@/components/ToastHost";
import AssignmentDetailPage from "@/pages/AssignmentDetailPage";
import ContactPage from "@/pages/ContactPage";
import FeedbackPage from "@/pages/FeedbackPage";
import AssignmentSearchPage from "@/pages/AssignmentSearchPage";
import DashboardPage from "@/pages/DashboardPage";
import AssignmentsPage from "@/pages/AssignmentsPage";
import CheckInPage from "@/pages/CheckInPage";
import HomePage from "@/pages/HomePage";
import FocusHistoryPage from "@/pages/FocusHistoryPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ImportPage from "@/pages/ImportPage";
import LoginPage from "@/pages/LoginPage";
import NotFoundPage from "@/pages/NotFoundPage";
import PlanningGuidePage from "@/pages/PlanningGuidePage";
import PlanPage from "@/pages/PlanPage";
import RegisterPage from "@/pages/RegisterPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import SettingsPage from "@/pages/SettingsPage";
import VerifyEmailPage from "@/pages/VerifyEmailPage";
import { restoreSession } from "@/lib/api";
import { useSignedIn } from "@/lib/useSignedIn";

export default function App() {
  const signedIn = useSignedIn();
  const [restored, setRestored] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!navOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setNavOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [navOpen]);

  useEffect(() => {
    // Wait for the saved session to be checked before routing, so pages do not flash the sign-in screen.
    void restoreSession().finally(() => setRestored(true));
  }, []);

  if (!restored) {
    return (
      <div className="page">
        <p className="muted">Loading…</p>
      </div>
    );
  }

  // Protected pages redirect to sign-in; sign-in pages redirect to the dashboard once signed in.
  const guard = (page: ReactElement) => (signedIn ? page : <Navigate to="/login" replace />);
  const guest = (page: ReactElement) => (signedIn ? <Navigate to="/dashboard" replace /> : page);

  const routes = (
    <Routes>
      <Route path="/" element={signedIn ? <Navigate to="/dashboard" replace /> : <HomePage />} />
      <Route path="/dashboard" element={guard(<DashboardPage />)} />
      <Route path="/login" element={guest(<LoginPage />)} />
      <Route path="/register" element={guest(<RegisterPage />)} />
      <Route path="/verify-email" element={guest(<VerifyEmailPage />)} />
      <Route path="/forgot-password" element={guest(<ForgotPasswordPage />)} />
      <Route path="/reset-password" element={guest(<ResetPasswordPage />)} />
      <Route path="/check-in" element={guard(<CheckInPage />)} />
      <Route path="/plan" element={guard(<PlanPage />)} />
      <Route path="/import" element={guard(<ImportPage />)} />
      <Route path="/assignments" element={guard(<AssignmentsPage />)} />
      <Route path="/assignments/search" element={guard(<AssignmentSearchPage />)} />
      <Route path="/focus/history" element={guard(<FocusHistoryPage />)} />
      <Route path="/assignments/:id" element={guard(<AssignmentDetailPage />)} />
      <Route path="/settings" element={guard(<SettingsPage />)} />
      <Route path="/feedback" element={guard(<FeedbackPage />)} />
      <Route path="/contact" element={<ContactPage />} />
      <Route path="/planning-guide" element={guard(<PlanningGuidePage />)} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );

  // Signed-out visitors get the public header and footer; signed-in users get the app shell.
  if (!signedIn) {
    return (
      <>
        <ToastHost />
        <PublicHeader />
        <main className="public-main">
          <div className="page">{routes}</div>
        </main>
        <SiteFooter />
      </>
    );
  }

  return (
    <>
      <ToastHost />
      <NavBar open={navOpen} onClose={() => setNavOpen(false)} />
      {navOpen && <button type="button" className="nav-backdrop" aria-label="Close menu" onClick={() => setNavOpen(false)} />}
      <div className="app-shell">
        <AppTopbar navOpen={navOpen} onToggleNav={() => setNavOpen((open) => !open)} />
        <main className="admin-main">
          <div className="page">{routes}</div>
        </main>
      </div>
    </>
  );
}
