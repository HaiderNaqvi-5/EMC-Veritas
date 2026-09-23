import { Skeleton } from "../../components/ui/Skeleton";
import { motion } from "framer-motion";

const cards = ["Active session", "Students", "Published activities", "Documents issued"];

export function AdminDashboard() {
  return <motion.section aria-labelledby="admin-overview" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}><div className="mb-8"><p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Operations</p><h1 id="admin-overview" className="mt-1 text-3xl font-bold tracking-tight">Admin overview</h1><p className="mt-2 max-w-2xl text-slate-600 dark:text-slate-400">Manage EMC student records, sessions, activities, and certificate operations.</p></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((label) => <article key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"><p className="text-sm font-medium text-slate-500">{label}</p><Skeleton className="mt-4 h-8 w-20" /><Skeleton className="mt-3 h-3 w-32" /></article>)}</div><section aria-label="Activity summary" className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><h2 className="font-semibold">Activity summary</h2><p className="mt-1 text-sm text-slate-500">Dashboard data will appear here when the operational API is available.</p><Skeleton className="mt-6 h-56 w-full" /></section></motion.section>;
}
