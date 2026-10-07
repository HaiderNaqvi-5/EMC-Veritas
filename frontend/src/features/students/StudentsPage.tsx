import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest, retryConnection } from "../../lib/api/client";
import { canonicalRollNumber } from "../../lib/utils";

type Student = {
  id: string;
  roll_number: string;
  full_name: string;
  active: boolean;
};

export function StudentsPage() {
  const client = useQueryClient();
  const [rollNumber, setRollNumber] = useState("");
  const [fullName, setFullName] = useState("");
  const [editingId, setEditingId] = useState("");
  const [editRollNumber, setEditRollNumber] = useState("");
  const [editFullName, setEditFullName] = useState("");
  const query = useQuery({
    queryKey: ["admin", "students"],
    queryFn: () => apiRequest<Student[]>("/admin/students"),
  });
  const create = useMutation({
    mutationFn: () =>
      apiRequest<Student>("/admin/students", {
        method: "POST",
        body: JSON.stringify({ roll_number: rollNumber, full_name: fullName }),
      }),
    onSuccess: () => {
      setRollNumber("");
      setFullName("");
      void client.invalidateQueries({ queryKey: ["admin", "students"] });
    },
  });
  const deactivate = useMutation({
    mutationFn: (id: string) =>
      apiRequest<Student>(`/admin/students/${id}/deactivate`, {
        method: "POST",
      }),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: ["admin", "students"] }),
  });
  const update = useMutation({
    mutationFn: (id: string) => apiRequest<Student>(`/admin/students/${id}`, {
      method: "PUT",
      body: JSON.stringify({ roll_number: editRollNumber, full_name: editFullName }),
    }),
    onSuccess: () => {
      setEditingId("");
      void client.invalidateQueries({ queryKey: ["admin", "students"] });
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => retryConnection(
      () => apiRequest<void>(`/admin/students/${id}`, { method: "DELETE", signal: AbortSignal.timeout(8_000) }),
      1,
    ),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin", "students"] }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  return (
    <section>
      <h1 className="text-3xl font-bold">Students</h1>
      <p className="mt-2 text-slate-600 dark:text-slate-400">
        Create, review, and deactivate EMC student records.
      </p>
      <form
        className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-3"
        onSubmit={submit}
      >
        <input
          required
          value={rollNumber}
          onChange={(e) => setRollNumber(canonicalRollNumber(e.target.value))}
          placeholder="Roll number"
          className="rounded border p-2"
        />
        <input
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Full name"
          className="rounded border p-2"
        />
        <button
          disabled={create.isPending}
          className="rounded bg-slate-900 p-2 text-white"
        >
          Add student
        </button>
        {create.isError && (
          <p role="alert" className="text-red-700 md:col-span-3">
            {create.error.message}
          </p>
        )}
      </form>
      {query.isLoading ? (
        <Skeleton className="mt-6 h-48 w-full" />
      ) : query.isError ? (
        <p role="alert" className="mt-6 rounded-lg bg-red-50 p-4 text-red-700">
          {query.error.message}
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                <th className="p-4">Roll number</th>
                <th className="p-4">Student</th>
                <th className="p-4">Status</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {query.data?.map((student) => (
                <tr key={student.id} className="border-b last:border-0">
                  <td className="p-4">{editingId === student.id ? <input required aria-label="Edit roll number" value={editRollNumber} onChange={(event) => setEditRollNumber(canonicalRollNumber(event.target.value))} className="w-full rounded border p-2"/> : student.roll_number}</td>
                  <td className="p-4">{editingId === student.id ? <input required aria-label="Edit student name" value={editFullName} onChange={(event) => setEditFullName(event.target.value)} className="w-full rounded border p-2"/> : student.full_name}</td>
                  <td className="p-4">
                    {student.active ? "Active" : "Deactivated"}
                  </td>
                  <td className="p-4">
                    {editingId === student.id ? (
                      <span className="flex flex-wrap gap-3">
                        <button onClick={() => update.mutate(student.id)} disabled={update.isPending || !editRollNumber.trim() || !editFullName.trim()} className="font-semibold underline">{update.isPending ? "Saving…" : "Save"}</button>
                        <button onClick={() => { setEditingId(""); update.reset(); }} disabled={update.isPending} className="underline">Cancel</button>
                      </span>
                    ) : student.active ? (
                      <span className="flex flex-wrap gap-3">
                        <button onClick={() => { setEditingId(student.id); setEditRollNumber(student.roll_number); setEditFullName(student.full_name); update.reset(); }} className="underline">Edit</button>
                        <button onClick={() => deactivate.mutate(student.id)} disabled={deactivate.isPending} className="underline">Deactivate</button>
                      </span>
                    ) : (
                      <span className="flex flex-wrap gap-3">
                        <button onClick={() => { setEditingId(student.id); setEditRollNumber(student.roll_number); setEditFullName(student.full_name); update.reset(); }} className="underline">Edit</button>
                        <button onClick={() => { if (window.confirm(`Delete ${student.full_name}? This cannot be undone.`)) remove.mutate(student.id); }} disabled={remove.isPending} className="text-red-700 underline disabled:opacity-60">Delete</button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {update.isError && <p role="alert" className="border-t bg-red-50 p-4 text-red-700">{update.error.message}</p>}
        </div>
      )}
    </section>
  );
}
