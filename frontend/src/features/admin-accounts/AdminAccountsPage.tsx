import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";

type Student = { id: string; roll_number: string; full_name: string; active: boolean };
type AdminAccount = {
  id: string;
  student_id: string;
  roll_number: string;
  full_name: string;
  role: "ADMIN" | "SUPER_ADMIN";
  active: boolean;
  must_change_password: boolean;
};

export function AdminAccountsPage() {
  const client = useQueryClient();
  const [studentId, setStudentId] = useState("");
  const [role, setRole] = useState<AdminAccount["role"]>("ADMIN");
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [message, setMessage] = useState("");

  const accounts = useQuery({ queryKey: ["admin", "accounts"], queryFn: () => apiRequest<AdminAccount[]>("/admin/admins") });
  const students = useQuery({ queryKey: ["admin", "students"], queryFn: () => apiRequest<Student[]>("/admin/students") });
  const refresh = () => void client.invalidateQueries({ queryKey: ["admin", "accounts"] });
  const create = useMutation({
    mutationFn: () => apiRequest<AdminAccount>("/admin/admins", { method: "POST", body: JSON.stringify({ student_id: studentId, role, temporary_password: temporaryPassword }) }),
    onSuccess: (account) => { setStudentId(""); setRole("ADMIN"); setTemporaryPassword(""); setMessage(`Created ${account.role.replace("_", " ")} access for ${account.full_name}. They must change the temporary password at first sign-in.`); refresh(); },
  });
  const deactivate = useMutation({
    mutationFn: (id: string) => apiRequest<AdminAccount>(`/admin/admins/${id}/deactivate`, { method: "POST" }),
    onSuccess: (account) => { setMessage(`Deactivated ${account.full_name}'s Admin account.`); refresh(); },
  });
  const resetPassword = useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) => apiRequest<AdminAccount>(`/admin/admins/${id}/reset-password`, { method: "POST", body: JSON.stringify({ temporary_password: password }) }),
    onSuccess: (account) => { setMessage(`Reset the password for ${account.full_name}. They must choose a new password when they sign in.`); refresh(); },
  });
  const existingStudentIds = new Set((accounts.data ?? []).map((account) => account.student_id));
  const eligibleStudents = (students.data ?? []).filter((student) => student.active && !existingStudentIds.has(student.id));
  const error = accounts.error?.message ?? students.error?.message ?? create.error?.message ?? deactivate.error?.message ?? resetPassword.error?.message;

  function submitCreate(event: FormEvent) { event.preventDefault(); setMessage(""); create.mutate(); }
  function submitReset(event: FormEvent<HTMLFormElement>, id: string) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("temporary_password") ?? "");
    setMessage("");
    resetPassword.mutate({ id, password });
    event.currentTarget.reset();
  }

  return <section>
    <h1 className="text-3xl font-bold">Admin accounts</h1>
    <p className="mt-2 text-slate-600 dark:text-slate-400">Create and manage privileged access. Every account is tied to an active student record and password changes are enforced by the server.</p>
    <form onSubmit={submitCreate} className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-4">
      <label className="grid gap-1 text-sm font-medium"><span>Student</span><select required value={studentId} onChange={(event) => setStudentId(event.target.value)} className="rounded border p-2 font-normal"><option value="">Choose an active student</option>{eligibleStudents.map((student) => <option key={student.id} value={student.id}>{student.roll_number} — {student.full_name}</option>)}</select></label>
      <label className="grid gap-1 text-sm font-medium"><span>Access level</span><select value={role} onChange={(event) => setRole(event.target.value as AdminAccount["role"])} className="rounded border p-2 font-normal"><option value="ADMIN">Admin</option><option value="SUPER_ADMIN">Super Admin</option></select></label>
      <label className="grid gap-1 text-sm font-medium"><span>Temporary password</span><input required minLength={12} type="password" autoComplete="new-password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} placeholder="At least 12 characters" className="rounded border p-2 font-normal" /></label>
      <button disabled={create.isPending || !eligibleStudents.length} className="self-end rounded bg-slate-900 p-2 text-white disabled:cursor-not-allowed disabled:opacity-60">{create.isPending ? "Creating…" : "Create account"}</button>
    </form>
    {!eligibleStudents.length && students.isSuccess && <p className="mt-2 text-sm text-slate-500">All active students already have an Admin account, or there are no active students to assign.</p>}
    {error && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {message && <p role="status" className="mt-4 rounded bg-green-50 p-3 text-green-800">{message}</p>}
    {accounts.isLoading ? <Skeleton className="mt-6 h-64 w-full" /> : <div className="mt-6 overflow-x-auto rounded-xl border"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600 dark:bg-slate-900 dark:text-slate-300"><tr><th className="p-3">Student</th><th className="p-3">Role</th><th className="p-3">Account state</th><th className="p-3">Password</th><th className="p-3">Actions</th></tr></thead><tbody>{accounts.data?.map((account) => <tr key={account.id} className="border-t"><td className="p-3"><strong>{account.full_name}</strong><br /><span className="text-slate-500">{account.roll_number}</span></td><td className="p-3">{account.role === "SUPER_ADMIN" ? "Super Admin" : "Admin"}</td><td className="p-3">{account.active ? "Active" : "Inactive"}</td><td className="p-3">{account.must_change_password ? "Change required" : "Current password set"}</td><td className="p-3"><div className="flex flex-wrap gap-2">{account.active && <details><summary className="cursor-pointer rounded border px-2 py-1">Reset password</summary><form onSubmit={(event) => submitReset(event, account.id)} className="mt-2 flex gap-2"><input name="temporary_password" required minLength={12} type="password" autoComplete="new-password" placeholder="Temporary password" className="w-48 rounded border p-2" /><button disabled={resetPassword.isPending} className="rounded border px-2 py-1">Save</button></form></details>}{account.active && <button disabled={deactivate.isPending} onClick={() => deactivate.mutate(account.id)} className="rounded border border-red-600 px-2 py-1 text-red-700">Deactivate</button>}</div></td></tr>)}</tbody></table></div>}
  </section>;
}
