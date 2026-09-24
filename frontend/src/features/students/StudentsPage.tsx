import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";

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
        className="mt-6 grid items-end gap-3 rounded-xl border p-4 md:grid-cols-3"
        onSubmit={submit}
      >
        <div className="flex flex-col gap-1.5">
          <label htmlFor="rollNumber" className="text-sm font-medium">
            Roll number <span className="text-red-500" aria-hidden="true">*</span>
          </label>
          <input
            id="rollNumber"
            required
            value={rollNumber}
            onChange={(e) => setRollNumber(e.target.value)}
            placeholder="Roll number"
            className="rounded border p-2"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="fullName" className="text-sm font-medium">
            Full name <span className="text-red-500" aria-hidden="true">*</span>
          </label>
          <input
            id="fullName"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
            className="rounded border p-2"
          />
        </div>
        <button
          disabled={create.isPending}
          className="rounded bg-slate-900 p-2 text-white disabled:cursor-not-allowed disabled:opacity-60 h-[42px]"
        >
          {create.isPending ? "Adding student..." : "Add student"}
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
                  <td className="p-4">{student.roll_number}</td>
                  <td className="p-4">{student.full_name}</td>
                  <td className="p-4">
                    {student.active ? "Active" : "Deactivated"}
                  </td>
                  <td className="p-4">
                    {student.active && (
                      <button
                        onClick={() => deactivate.mutate(student.id)}
                        disabled={deactivate.isPending}
                        className="underline"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
