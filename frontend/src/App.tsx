import { type ReactElement, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router";

import AppTopbar from "@/components/AppTopbar";
import NavBar from "@/components/NavBar";
import PublicHeader from "@/components/PublicHeader";
import SiteFooter from "@/components/SiteFooter";
import ToastHost from "@/components/ToastHost";
import AssignmentDetailPage from "@/pages/AssignmentDetailPage";
import AssignmentSearchPage from "@/pages/AssignmentSearchPage";
import AssignmentsPage from "@/pages/AssignmentsPage";
import CheckInPage from "@/pages/CheckInPage";
import HomePage from "@/pages/HomePage";
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

  useEffect(() => {
    restoreSession().finally(() => setRestored(true));
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
  const guest = (page: ReactElement) => (signedIn ? <Navigate to="/assignments" replace /> : page);

  const routes = (
    <Routes>
      <Route path="/" element={signedIn ? <Navigate to="/assignments" replace /> : <HomePage />} />
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
      <Route path="/assignments/:id" element={guard(<AssignmentDetailPage />)} />
      <Route path="/settings" element={guard(<SettingsPage />)} />
      <Route path="/planning-guide" element={guard(<PlanningGuidePage />)} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );

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
      <NavBar />
      <div className="app-shell">
        <AppTopbar />
        <main className="admin-main">
          <div className="page">{routes}</div>
        </main>
      </div>
    </>
  );
}
