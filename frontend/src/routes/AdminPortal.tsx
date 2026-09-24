import { type ReactNode, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AdminShell } from "../components/layout/AdminShell";
import { AdminDashboard } from "../features/admin/AdminDashboard";
import { StudentsPage } from "../features/students/StudentsPage";
import { SessionsPage } from "../features/sessions/SessionsPage";
import { ActivitiesPage } from "../features/activities/ActivitiesPage";
import { ImportsPage } from "../features/imports/ImportsPage";
import { SignatoriesPage } from "../features/signatories/SignatoriesPage";
import { ExecutiveMembershipsPage } from "../features/executive-memberships/ExecutiveMembershipsPage";
import { AuditLogPage } from "../features/audit/AuditLogPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { LeadershipTemplatesPage } from "../features/leadership-templates/LeadershipTemplatesPage";
import { TemporaryPasswordChange } from "../features/auth/TemporaryPasswordChange";
import { authApi } from "../features/auth/contracts";
import { SESSION_EXPIRED_EVENT } from "../lib/api/client";
import { TemplateEditorPage } from "../features/templates/TemplateEditorPage";

export function AdminPortal() {
  const client = useQueryClient(); const [dismissed, setDismissed] = useState(false); const [sessionExpired, setSessionExpired] = useState(false);
  const session = useQuery({ queryKey: ["admin", "session"], queryFn: authApi.currentSession });
  useEffect(() => { const expired = () => setSessionExpired(true); window.addEventListener(SESSION_EXPIRED_EVENT, expired); return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expired); }, []);
  const mustChangePassword = session.data?.authenticated && session.data.temporary_password_change_required && !dismissed;
  if (session.isLoading) return <main className="min-h-screen bg-slate-50 p-8 dark:bg-slate-950"><p className="text-sm text-slate-600 dark:text-slate-400">Checking your Admin session…</p></main>;
  if (session.isError || !session.data?.authenticated || !session.data.role) return <Navigate to="/" replace />;
  if (sessionExpired) return <Navigate to="/" replace />;
  const superAdminOnly = (element: ReactNode) => session.data.role === "SUPER_ADMIN" ? element : <Navigate to="/admin" replace />;
  return <>{mustChangePassword && <TemporaryPasswordChange onComplete={() => { setDismissed(true); void client.invalidateQueries({ queryKey: ["admin", "session"] }); }} />}<Routes><Route element={<AdminShell role={session.data.role} />}><Route index element={<AdminDashboard />} /><Route path="students" element={<StudentsPage />} /><Route path="activities" element={<ActivitiesPage />} /><Route path="sessions" element={<SessionsPage />} /><Route path="imports" element={<ImportsPage />} /><Route path="signatories" element={<SignatoriesPage />} /><Route path="executive-memberships" element={<ExecutiveMembershipsPage />} /><Route path="templates" element={superAdminOnly(<TemplateEditorPage />)} /><Route path="leadership-templates" element={superAdminOnly(<LeadershipTemplatesPage />)} /><Route path="documents" element={<DocumentsPage />} /><Route path="audit" element={superAdminOnly(<AuditLogPage />)} /><Route path="*" element={<Navigate to="/admin" replace />} /></Route></Routes></>;
}
