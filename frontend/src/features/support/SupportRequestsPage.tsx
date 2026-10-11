import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  listSupportRequests,
  supportCategoryLabels,
  updateSupportRequest,
  type SupportRequest,
  type SupportRequestStatus,
} from "../../api/support";
import { Skeleton } from "../../components/ui/Skeleton";

const statusLabels: Record<SupportRequestStatus, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function RequestDetail({ request }: { request: SupportRequest }) {
  const cache = useQueryClient();
  const [status, setStatus] = useState(request.status);
  const [adminNotes, setAdminNotes] = useState(request.admin_notes ?? "");
  const [resolutionMessage, setResolutionMessage] = useState(request.resolution_message ?? "");
  const update = useMutation({
    mutationFn: () => updateSupportRequest(request.id, {
      status,
      admin_notes: adminNotes || null,
      resolution_message: resolutionMessage || null,
    }),
    onSuccess: () => void cache.invalidateQueries({ queryKey: ["admin", "support-requests"] }),
  });

  useEffect(() => {
    setStatus(request.status);
    setAdminNotes(request.admin_notes ?? "");
    setResolutionMessage(request.resolution_message ?? "");
    update.reset();
  }, [request.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const mailSubject = encodeURIComponent(`[${request.ticket_number}] EMC Veritas support`);
  const mailBody = encodeURIComponent(`${resolutionMessage || "Hello,\n\nWe are following up on your EMC Veritas support request.\n\n"}\n\nReference: ${request.ticket_number}`);

  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5 dark:border-slate-800">
      <div><p className="text-xs font-bold uppercase tracking-[.15em] text-indigo-600 dark:text-indigo-400">{request.ticket_number}</p><h2 className="mt-2 text-2xl font-bold">{request.full_name}</h2><p className="mt-1 text-sm text-slate-500">{request.roll_number} · Submitted {formatDate(request.created_at)}</p></div>
      <span className={`rounded-full px-3 py-1 text-xs font-bold ${request.status === "RESOLVED" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200" : request.status === "IN_PROGRESS" ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200" : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200"}`}>{statusLabels[request.status]}</span>
    </div>
    <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
      <div><dt className="font-semibold text-slate-500">Contact email</dt><dd className="mt-1 break-all font-medium">{request.contact_email}</dd></div>
      <div><dt className="font-semibold text-slate-500">Problem type</dt><dd className="mt-1 font-medium">{supportCategoryLabels[request.problem_category as keyof typeof supportCategoryLabels] ?? request.problem_category}</dd></div>
    </dl>
    <section className="mt-5 rounded-xl bg-slate-50 p-4 dark:bg-slate-950"><h3 className="text-sm font-semibold">Student’s description</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-300">{request.problem_details}</p></section>
    <div className="mt-5 grid gap-4">
      <label className="text-sm font-semibold">Status<select className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5 dark:border-slate-700 dark:bg-slate-950" value={status} onChange={(event) => setStatus(event.target.value as SupportRequestStatus)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="text-sm font-semibold">Internal notes<textarea className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-3 font-normal dark:border-slate-700 dark:bg-slate-950" rows={3} value={adminNotes} onChange={(event) => setAdminNotes(event.target.value)} placeholder="Visible only to administrators" /></label>
      <label className="text-sm font-semibold">Reply or resolution message<textarea className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-3 font-normal dark:border-slate-700 dark:bg-slate-950" rows={4} value={resolutionMessage} onChange={(event) => setResolutionMessage(event.target.value)} placeholder="Write the response you want to send to the student" /></label>
    </div>
    {update.isError && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-200">{update.error.message}</p>}
    {update.isSuccess && <p role="status" className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200">Request updated and recorded in the audit log.</p>}
    <div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={update.isPending} onClick={() => update.mutate()} className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{update.isPending ? "Saving…" : "Save request"}</button><a className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800" href={`mailto:${request.contact_email}?subject=${mailSubject}&body=${mailBody}`}>Reply by email ↗</a></div>
  </article>;
}

export function SupportRequestsPage() {
  const [status, setStatus] = useState<SupportRequestStatus | "">("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const allRequests = useQuery({ queryKey: ["admin", "support-requests", "summary"], queryFn: () => listSupportRequests(), staleTime: 15_000 });
  const requests = useQuery({ queryKey: ["admin", "support-requests", status, search], queryFn: () => listSupportRequests(status || undefined, search), staleTime: 15_000 });
  const counts = useMemo(() => ({
    open: allRequests.data?.filter((item) => item.status === "OPEN").length ?? 0,
    progress: allRequests.data?.filter((item) => item.status === "IN_PROGRESS").length ?? 0,
    resolved: allRequests.data?.filter((item) => item.status === "RESOLVED").length ?? 0,
  }), [allRequests.data]);
  const selected = requests.data?.find((item) => item.id === selectedId) ?? requests.data?.[0];

  return <section aria-labelledby="support-title">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Student care</p><h1 id="support-title" className="mt-1 text-3xl font-bold tracking-tight">Support requests</h1><p className="mt-2 max-w-2xl text-slate-600 dark:text-slate-400">Investigate missing or incorrect records, keep private notes, and reply using the student’s contact email.</p></div><div className="flex gap-2 text-xs font-semibold"><span className="rounded-full bg-red-100 px-3 py-1.5 text-red-800 dark:bg-red-950 dark:text-red-200">{counts.open} open</span><span className="rounded-full bg-amber-100 px-3 py-1.5 text-amber-800 dark:bg-amber-950 dark:text-amber-200">{counts.progress} active</span><span className="rounded-full bg-emerald-100 px-3 py-1.5 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">{counts.resolved} resolved</span></div></div>
    <div className="mt-6 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:grid-cols-[1fr_13rem]"><label className="text-sm font-semibold">Search<input value={search} onChange={(event) => setSearch(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5 font-normal dark:border-slate-700 dark:bg-slate-950" placeholder="Ticket, roll number, name, or email" /></label><label className="text-sm font-semibold">Status<select value={status} onChange={(event) => setStatus(event.target.value as SupportRequestStatus | "")} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5 font-normal dark:border-slate-700 dark:bg-slate-950"><option value="">All requests</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
    {requests.isLoading ? <Skeleton className="mt-6 h-80 w-full" /> : requests.isError ? <p role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-red-700 dark:bg-red-950/30 dark:text-red-200">{requests.error.message}</p> : !requests.data?.length ? <div className="mt-6 rounded-2xl border border-dashed border-slate-300 p-10 text-center dark:border-slate-700"><h2 className="text-lg font-semibold">No matching requests</h2><p className="mt-2 text-sm text-slate-500">New student submissions will appear here.</p></div> : <div className="mt-6 grid gap-5 lg:grid-cols-[21rem_minmax(0,1fr)]"><nav aria-label="Support request list" className="space-y-2">{requests.data.map((item) => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`w-full rounded-xl border p-4 text-left transition ${selected?.id === item.id ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500/20 dark:bg-indigo-950/40" : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"}`}><span className="flex items-center justify-between gap-3"><strong className="text-sm">{item.full_name}</strong><i className={`h-2.5 w-2.5 rounded-full ${item.status === "OPEN" ? "bg-red-500" : item.status === "IN_PROGRESS" ? "bg-amber-500" : "bg-emerald-500"}`} /></span><span className="mt-1 block text-xs text-slate-500">{item.roll_number} · {item.ticket_number}</span><span className="mt-3 block truncate text-sm text-slate-600 dark:text-slate-300">{supportCategoryLabels[item.problem_category as keyof typeof supportCategoryLabels] ?? item.problem_category}</span></button>)}</nav>{selected && <RequestDetail key={selected.id} request={selected} />}</div>}
  </section>;
}
