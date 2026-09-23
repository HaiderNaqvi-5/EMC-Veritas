import { Navigate, Route, Routes } from "react-router-dom";
import { AdminShell } from "../components/layout/AdminShell";
import { AdminDashboard } from "../features/admin/AdminDashboard";
import { StudentsPage } from "../features/students/StudentsPage";
import { SessionsPage } from "../features/sessions/SessionsPage";
import { ActivitiesPage } from "../features/activities/ActivitiesPage";
import { ImportsPage } from "../features/imports/ImportsPage";
import { SignatoriesPage } from "../features/signatories/SignatoriesPage";
import { TemplatesPage } from "../features/templates/TemplatesPage";
import { AuditLogPage } from "../features/audit/AuditLogPage";

export function AdminPortal() {
  return <Routes><Route element={<AdminShell />}><Route index element={<AdminDashboard />} /><Route path="students" element={<StudentsPage />} /><Route path="activities" element={<ActivitiesPage />} /><Route path="sessions" element={<SessionsPage />} /><Route path="imports" element={<ImportsPage />} /><Route path="signatories" element={<SignatoriesPage />} /><Route path="templates" element={<TemplatesPage />} /><Route path="audit" element={<AuditLogPage />} /><Route path="*" element={<Navigate to="/admin" replace />} /></Route></Routes>;
}
