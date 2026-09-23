import { Navigate, Route, Routes } from "react-router-dom";
import { AdminShell } from "../components/layout/AdminShell";
import { AdminDashboard } from "../features/admin/AdminDashboard";

function PendingPage({ title }: { title: string }) {
  return <section aria-labelledby="page-title"><h1 id="page-title" className="text-3xl font-bold">{title}</h1><div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"><h2 className="font-semibold">Coming in Phase A2</h2><p className="mt-2 text-slate-600 dark:text-slate-400">This area is intentionally unavailable until its server-side contract and data rules are ready.</p></div></section>;
}

export function AdminPortal() {
  return <Routes><Route element={<AdminShell />}><Route index element={<AdminDashboard />} /><Route path="students" element={<PendingPage title="Students" />} /><Route path="activities" element={<PendingPage title="Activities" />} /><Route path="sessions" element={<PendingPage title="Sessions" />} /><Route path="imports" element={<PendingPage title="Imports" />} /><Route path="*" element={<Navigate to="/admin" replace />} /></Route></Routes>;
}
