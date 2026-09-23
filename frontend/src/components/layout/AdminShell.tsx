import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";
import { authApi } from "../../features/auth/contracts";

const navigation = [
  ["Overview", "/admin"],
  ["Students", "/admin/students"],
  ["Activities", "/admin/activities"],
  ["Sessions", "/admin/sessions"],
  ["Imports", "/admin/imports"],
  ["Signatories", "/admin/signatories"],
  ["Certificate templates", "/admin/templates"],
  ["Leadership templates", "/admin/leadership-templates"],
  ["Documents", "/admin/documents"],
  ["Audit log", "/admin/audit"],
];

export function AdminShell() {
  const navigate = useNavigate();
  async function logout() { await authApi.logout(); navigate("/"); }
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-slate-50">
      <aside className="fixed inset-y-0 hidden w-64 border-r border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 lg:block">
        <Brand />
        <nav aria-label="Admin navigation" className="mt-10 space-y-1">
          {navigation.map(([label, path]) => <NavigationLink key={path} label={label} path={path} />)}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95 sm:px-8">
          <div className="flex items-center gap-3 lg:hidden"><Brand compact /></div>
          <div className="ml-auto flex items-center gap-4"><ThemeToggle /><button onClick={() => void logout()} className="text-sm underline">Sign out</button><div className="text-right"><p className="text-sm font-semibold">Admin portal</p><p className="text-xs text-slate-500">EMC Veritas</p></div></div>
        </header>
        <nav aria-label="Admin navigation" className="flex gap-2 overflow-x-auto border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 lg:hidden">
          {navigation.map(([label, path]) => <NavigationLink key={path} label={label} path={path} />)}
        </nav>
        <main className="mx-auto max-w-7xl p-4 sm:p-8"><Outlet /></main>
      </div>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="flex items-center gap-3"><div aria-label="EMC logo slot" className="grid h-10 w-10 place-items-center rounded-xl border border-dashed border-slate-400 text-xs font-bold text-slate-500">EMC</div>{!compact && <div><p className="font-bold">EMC Veritas</p><p className="text-xs text-slate-500">Admin workspace</p></div>}</div>;
}

function NavigationLink({ label, path }: { label: string; path: string }) {
  return <NavLink end={path === "/admin"} to={path} className={({ isActive }) => `block whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}>{label}</NavLink>;
}
