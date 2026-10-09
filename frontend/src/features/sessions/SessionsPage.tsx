import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";

type EmcSession = {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
};
export function SessionsPage() {
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const query = useQuery({
    queryKey: ["admin", "sessions"],
    queryFn: () => apiRequest<EmcSession[]>("/admin/sessions"),
  });
  const refresh = () =>
    client.invalidateQueries({ queryKey: ["admin", "sessions"] });
  const create = useMutation({
    mutationFn: () =>
      apiRequest<EmcSession>("/admin/sessions", {
        method: "POST",
        body: JSON.stringify({ name, start_date: start, end_date: end }),
      }),
    onSuccess: () => {
      setName("");
      setStart("");
      setEnd("");
      void refresh();
    },
  });
  const close = useMutation({
    mutationFn: (id: string) =>
      apiRequest<EmcSession>(`/admin/sessions/${id}/close`, { method: "POST" }),
    onSuccess: () => void refresh(),
  });
  const update = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Omit<EmcSession, "id" | "status">;
    }) =>
      apiRequest<EmcSession>(`/admin/sessions/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => void refresh(),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  function edit(event: FormEvent<HTMLFormElement>, item: EmcSession) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    update.mutate({
      id: item.id,
      payload: {
        name: String(data.get("name")),
        start_date: String(data.get("start_date")),
        end_date: String(data.get("end_date")),
      },
    });
  }
  const error =
    create.error?.message ?? close.error?.message ?? update.error?.message;
  const activeSession = query.data?.find((item) => item.status === "ACTIVE");
  return (
    <section>
      <h1 className="text-3xl font-bold">Sessions</h1>
      <p className="mt-2 text-slate-600 dark:text-slate-400">
        Only one EMC session can be active at a time. Historical sessions stay
        retained.
      </p>
      {query.isLoading ? <Skeleton className="mt-6 h-32 w-full" /> : query.isError ? <div role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-red-700 dark:bg-red-950/30 dark:text-red-200">Could not load sessions. {query.error.message}<button onClick={() => void query.refetch()} className="ml-2 underline">Retry</button></div> : activeSession ? <section className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50 p-5 dark:border-indigo-900 dark:bg-indigo-950/30"><p className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">Current session</p><h2 className="mt-1 text-xl font-bold">{activeSession.name}</h2><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{activeSession.start_date} to {activeSession.end_date} · Status: {activeSession.status}</p><p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Closing ends this active session’s lifecycle. Historical records remain available.</p></section> : <section className="mt-6 rounded-xl border border-dashed p-5 text-sm text-slate-500">No active session. Create one when the next EMC term is ready to begin.</section>}
      <form
        className={`mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-4 ${activeSession ? "bg-slate-50 opacity-75 dark:bg-slate-900" : "bg-white dark:bg-slate-900"}`}
        onSubmit={submit}
      >
        <input
          aria-label="Session start date"
          required
          className="rounded border p-2"
          placeholder="Session name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          aria-label="Session end date"
          required
          className="rounded border p-2"
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <input
          required
          className="rounded border p-2"
          type="date"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />
        <button
          className="rounded bg-slate-900 p-2 text-white"
          disabled={create.isPending}
        >
          {create.isPending ? "Creating…" : "Create active session"}
        </button>
      </form>
      {activeSession && <p className="mt-2 text-sm text-slate-500">Only one session may be active at a time.</p>}
      {error && (
        <p role="alert" className="mt-3 text-red-700">
          {error}
        </p>
      )}
      {!query.isLoading && !query.isError && (
        <ul className="mt-6 space-y-2">
          <h2 className="text-lg font-semibold">Session history</h2>
          {!query.data?.length && <li className="rounded-xl border border-dashed p-4 text-sm text-slate-500">No sessions have been created yet.</li>}
          {query.data?.map((item) => (
            <li key={item.id} className="rounded border p-3">
              <div className="flex items-center justify-between gap-3">
                <span>
                  {item.name} — {item.start_date} to {item.end_date} —{" "}
                  {item.status}
                </span>
                {item.status === "ACTIVE" && (
                  <button
                    disabled={close.isPending}
                    onClick={() => close.mutate(item.id)}
                    className="rounded border border-red-600 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                  >
                    {close.isPending ? "Closing…" : "Close session"}
                  </button>
                )}
              </div>
              <details className="mt-3">
                <summary className="cursor-pointer text-sm underline">
                  Edit session
                </summary>
                <form
                  onSubmit={(event) => edit(event, item)}
                  className="mt-3 grid gap-2 md:grid-cols-4"
                >
                  <input
                    aria-label={`Name for ${item.name}`}
                    name="name"
                    defaultValue={item.name}
                    required
                    className="rounded border p-2"
                  />
                  <input
                    aria-label={`Start date for ${item.name}`}
                    name="start_date"
                    defaultValue={item.start_date}
                    required
                    type="date"
                    className="rounded border p-2"
                  />
                  <input
                    aria-label={`End date for ${item.name}`}
                    name="end_date"
                    defaultValue={item.end_date}
                    required
                    type="date"
                    className="rounded border p-2"
                  />
                  <button
                    disabled={update.isPending}
                    className="rounded border p-2"
                  >
                    Save changes
                  </button>
                </form>
              </details>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
