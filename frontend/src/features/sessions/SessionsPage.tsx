import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";

type EmcSession = { id: string; name: string; start_date: string; end_date: string; status: string };
export function SessionsPage() {
  const client = useQueryClient(); const [name, setName] = useState(""); const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const query = useQuery({ queryKey: ["admin", "sessions"], queryFn: () => apiRequest<EmcSession[]>("/admin/sessions") });
  const refresh = () => client.invalidateQueries({ queryKey: ["admin", "sessions"] });
  const create = useMutation({ mutationFn: () => apiRequest<EmcSession>("/admin/sessions", { method: "POST", body: JSON.stringify({ name, start_date: start, end_date: end }) }), onSuccess: () => { setName(""); setStart(""); setEnd(""); void refresh(); } });
  const close = useMutation({ mutationFn: (id: string) => apiRequest<EmcSession>(`/admin/sessions/${id}/close`, { method: "POST" }), onSuccess: () => void refresh() });
  function submit(event: FormEvent) { event.preventDefault(); create.mutate(); }
  return <section><h1 className="text-3xl font-bold">Sessions</h1><p className="mt-2 text-slate-600 dark:text-slate-400">Only one EMC session can be active at a time.</p><form className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-4" onSubmit={submit}><input required className="rounded border p-2" placeholder="Session name" value={name} onChange={(e) => setName(e.target.value)}/><input required className="rounded border p-2" type="date" value={start} onChange={(e) => setStart(e.target.value)}/><input required className="rounded border p-2" type="date" value={end} onChange={(e) => setEnd(e.target.value)}/><button className="rounded bg-slate-900 p-2 text-white" disabled={create.isPending}>Create active session</button>{create.isError && <p role="alert" className="text-red-700 md:col-span-4">{create.error.message}</p>}</form>{query.isLoading ? <Skeleton className="mt-6 h-40 w-full"/> : query.isError ? <p role="alert" className="mt-6 text-red-700">{query.error.message}</p> : <ul className="mt-6 space-y-2">{query.data?.map((item) => <li key={item.id} className="flex items-center justify-between rounded border p-3"><span>{item.name} — {item.start_date} to {item.end_date} — {item.status}</span>{item.status === "ACTIVE" && <button disabled={close.isPending} onClick={() => close.mutate(item.id)} className="underline">Close session</button>}</li>)}</ul>}</section>;
}
