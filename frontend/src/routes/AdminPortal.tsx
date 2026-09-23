import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AdminShell } from "../components/layout/AdminShell";
import { AdminDashboard } from "../features/admin/AdminDashboard";
import { StudentsPage } from "../features/students/StudentsPage";
import { SessionsPage } from "../features/sessions/SessionsPage";
import { ActivitiesPage } from "../features/activities/ActivitiesPage";
import { ImportsPage } from "../features/imports/ImportsPage";
import { SignatoriesPage } from "../features/signatories/SignatoriesPage";
import { TemplatesPage } from "../features/templates/TemplatesPage";
import { AuditLogPage } from "../features/audit/AuditLogPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { LeadershipTemplatesPage } from "../features/leadership-templates/LeadershipTemplatesPage";
import { TemporaryPasswordChange } from "../features/auth/TemporaryPasswordChange";
import { authApi } from "../features/auth/contracts";
import { SESSION_EXPIRED_EVENT } from "../lib/api/client";

export function AdminPortal() {
  const client = useQueryClient(); const [dismissed, setDismissed] = useState(false); const [sessionExpired, setSessionExpired] = useState(false);
  const session = useQuery({ queryKey: ["admin", "session"], queryFn: authApi.currentSession });
  useEffect(() => { const expired = () => setSessionExpired(true); window.addEventListener(SESSION_EXPIRED_EVENT, expired); return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expired); }, []);
  const mustChangePassword = session.data?.authenticated && session.data.temporary_password_change_required && !dismissed;
  if (sessionExpired) return <Navigate to="/" replace />;
  return <>{mustChangePassword && <TemporaryPasswordChange onComplete={() => { setDismissed(true); void client.invalidateQueries({ queryKey: ["admin", "session"] }); }} />}<Routes><Route element={<AdminShell />}><Route index element={<AdminDashboard />} /><Route path="students" element={<StudentsPage />} /><Route path="activities" element={<ActivitiesPage />} /><Route path="sessions" element={<SessionsPage />} /><Route path="imports" element={<ImportsPage />} /><Route path="signatories" element={<SignatoriesPage />} /><Route path="templates" element={<TemplatesPage />} /><Route path="leadership-templates" element={<LeadershipTemplatesPage />} /><Route path="documents" element={<DocumentsPage />} /><Route path="audit" element={<AuditLogPage />} /><Route path="*" element={<Navigate to="/admin" replace />} /></Route></Routes></>;
}
