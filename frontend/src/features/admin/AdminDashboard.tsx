import { lazy, Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";

type Student = { active: boolean };
type EmcSession = { status: string };
type Activity = { status: string };
const ActivityChart = lazy(() => import("./ActivityChart"));

export function AdminDashboard() {
  const students = useQuery({ queryKey: ["admin", "students"], queryFn: () => apiRequest<Student[]>("/admin/students") });
  const sessions = useQuery({ queryKey: ["admin", "sessions"], queryFn: () => apiRequest<EmcSession[]>("/admin/sessions") });
  const activities = useQuery({ queryKey: ["admin", "activities"], queryFn: () => apiRequest<Activity[]>("/admin/activities") });
  const loading = students.isLoading || sessions.isLoading || activities.isLoading;
  const error = students.error?.message ?? sessions.error?.message ?? activities.error?.message;
  const activeStudents = students.data?.filter((item) => item.active).length ?? 0;
  const activeSessions = sessions.data?.filter((item) => item.status === "ACTIVE").length ?? 0;
  const publishedActivities = activities.data?.filter((item) => item.status === "PUBLISHED").length ?? 0;
  const chart = ["DRAFT", "READY", "PUBLISHED", "ARCHIVED"].map((status) => ({ status, count: activities.data?.filter((item) => item.status === status).length ?? 0 }));
  const cards = [["Active session", activeSessions], ["Active students", activeStudents], ["Published activities", publishedActivities], ["All activities", activities.data?.length ?? 0]];
  return <motion.section aria-labelledby="admin-overview" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}><div className="mb-8"><p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Operations</p><h1 id="admin-overview" className="mt-1 text-3xl font-bold tracking-tight">Admin overview</h1><p className="mt-2 max-w-2xl text-slate-600 dark:text-slate-400">Live operational records are shown below. Data-only areas stay visible while the API starts.</p></div>{error && <p role="alert" className="mb-6 rounded-lg bg-red-50 p-4 text-red-700">{error}</p>}<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value]) => <article key={String(label)} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"><p className="text-sm font-medium text-slate-500">{label}</p>{loading ? <Skeleton className="mt-4 h-8 w-20" /> : <p className="mt-3 text-3xl font-bold">{value}</p>}</article>)}</div><section aria-label="Activity summary" className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><h2 className="font-semibold">Activity summary</h2><p className="mt-1 text-sm text-slate-500">Current activity counts by lifecycle status.</p>{loading ? <Skeleton className="mt-6 h-56 w-full" /> : <Suspense fallback={<Skeleton className="mt-6 h-56 w-full"/>}><ActivityChart data={chart}/></Suspense>}</section></motion.section>;
}
