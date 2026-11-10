import { Navigate, Route, Routes } from "react-router";

import NavBar from "@/components/NavBar";
import AssignmentDetailPage from "@/pages/AssignmentDetailPage";
import AssignmentsPage from "@/pages/AssignmentsPage";
import HomePage from "@/pages/HomePage";
import ImportPage from "@/pages/ImportPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";

export default function App() {
  return (
    <>
      <NavBar />
      <main className="admin-main">
        <div className="page">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/assignments" element={<AssignmentsPage />} />
            <Route path="/assignments/:id" element={<AssignmentDetailPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </>
  );
}
