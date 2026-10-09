import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../lib/api/client";

type IssueResult = { issue_date: string; issued_document_ids: string[]; skipped_student_ids: string[] };
type ReissueResult = { replacement_document_id: string; issue_date: string; version: number };
type PreGenerationResult = { total_documents: number; ready_documents: number; generated_documents: number; remaining_documents: number; failed_document_ids: string[] };
type ActivityRevokeResult = { activity_id: string; student_id: string | null; revoked_document_ids: string[] };
type DocumentListItem = {
  id: string; student_id: string; student_name: string; roll_number: string; activity_id: string | null;
  document_type: string; verification_id: string; issue_date: string; status: string; version: number;
  storage_key: string | null;
};
type Activity = { id: string; name: string; activity_date: string; status: string };

export function DocumentsPage() {
  const client = useQueryClient();
  const [activityId, setActivityId] = useState("");
  const [preGenerationActivityId, setPreGenerationActivityId] = useState("");
  const [ecPreGenerationActivityId, setEcPreGenerationActivityId] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [revokeActivityId, setRevokeActivityId] = useState("");
  const [studentDocumentId, setStudentDocumentId] = useState("");
  const [message, setMessage] = useState("");
  const documents = useQuery({ queryKey: ["admin", "documents"], queryFn: () => apiRequest<DocumentListItem[]>("/admin/documents") });
  const activities = useQuery({ queryKey: ["admin", "activities"], queryFn: () => apiRequest<Activity[]>("/admin/activities") });
  const refreshDocuments = () => void client.invalidateQueries({ queryKey: ["admin", "documents"] });
  const issue = useMutation({
    mutationFn: () => apiRequest<IssueResult>(`/admin/documents/activities/${activityId}/issue`, { method: "POST" }),
    onSuccess: (result) => { setMessage(`Issued ${result.issued_document_ids.length} records on ${result.issue_date}; ${result.skipped_student_ids.length} existing valid records were skipped.`); refreshDocuments(); },
  });
  const preGenerate = useMutation({
    mutationFn: () => apiRequest<PreGenerationResult>(`/admin/documents/activities/${preGenerationActivityId}/pre-generate?limit=5`, { method: "POST" }),
    onSuccess: refreshDocuments,
  });
  const preGenerateEc = useMutation({
    mutationFn: () => apiRequest<PreGenerationResult>(`/admin/documents/activities/${ecPreGenerationActivityId}/pre-generate-ec?limit=5`, { method: "POST" }),
    onSuccess: refreshDocuments,
  });
  const revoke = useMutation({
    mutationFn: () => apiRequest<void>(`/admin/documents/${documentId}/revoke`, { method: "POST" }),
    onSuccess: () => { setDocumentId(""); setMessage("Document revoked and removed from the operational document list."); refreshDocuments(); },
  });
  const reissue = useMutation({
    mutationFn: () => apiRequest<ReissueResult>(`/admin/documents/${documentId}/reissue`, { method: "POST" }),
    onSuccess: (result) => { setDocumentId(""); setMessage(`New version ${result.version} reserved for ${result.issue_date}: ${result.replacement_document_id}`); refreshDocuments(); },
  });
  const operationalDocuments = documents.data?.filter((item) => item.status === "VALID") ?? [];
  const activityCertificates = useMemo(
    () => operationalDocuments.filter((item) => item.document_type === "ACTIVITY_CERTIFICATE" && item.activity_id),
    [operationalDocuments],
  );
  const ecCertificates = useMemo(
    () => operationalDocuments.filter((item) => item.document_type === "EXECUTIVE_COUNCIL_CERTIFICATE" && item.activity_id),
    [operationalDocuments],
  );
  const revocableActivities = useMemo(() => {
    const ids = new Set(activityCertificates.map((item) => item.activity_id));
    return (activities.data ?? []).filter((item) => ids.has(item.id));
  }, [activities.data, activityCertificates]);
  const studentActivityDocuments = useMemo(
    () => activityCertificates.filter((item) => item.activity_id === revokeActivityId),
    [activityCertificates, revokeActivityId],
  );
  const revokeActivity = useMutation({
    mutationFn: () => apiRequest<ActivityRevokeResult>(`/admin/documents/activities/${revokeActivityId}/revoke`, { method: "POST" }),
    onSuccess: (result) => { setMessage(`${result.revoked_document_ids.length} certificate(s) were revoked for the selected activity.`); setStudentDocumentId(""); refreshDocuments(); },
  });
  const revokeStudent = useMutation({
    mutationFn: () => {
      const document = studentActivityDocuments.find((item) => item.id === studentDocumentId);
      if (!document) throw new Error("Choose a student certificate to revoke.");
      return apiRequest<ActivityRevokeResult>(`/admin/documents/activities/${revokeActivityId}/students/${document.student_id}/revoke`, { method: "POST" });
    },
    onSuccess: (result) => { setMessage(`${result.revoked_document_ids.length} certificate(s) were revoked for the selected student.`); setStudentDocumentId(""); refreshDocuments(); },
  });
  function submitIssue(event: FormEvent) { event.preventDefault(); setMessage(""); issue.mutate(); }
  function submitDocument(event: FormEvent, action: "revoke" | "reissue") { event.preventDefault(); setMessage(""); if (action === "revoke") revoke.mutate(); else reissue.mutate(); }
  const error = issue.error?.message ?? preGenerate.error?.message ?? preGenerateEc.error?.message ?? revoke.error?.message ?? revokeActivity.error?.message ?? revokeStudent.error?.message ?? reissue.error?.message ?? activities.error?.message;
  const readyActivities = activities.data?.filter((item) => item.status === "READY") ?? [];
  const issuableActivities = activities.data?.filter((item) => item.status === "READY" || item.status === "PUBLISHED") ?? [];
  const publishedActivities = activities.data?.filter((item) => item.status === "PUBLISHED") ?? [];
  const ecActivityIds = new Set(ecCertificates.map((item) => item.activity_id));
  const ecActivities = (activities.data ?? []).filter((item) => ecActivityIds.has(item.id));
  const selectedActivity = revocableActivities.find((item) => item.id === revokeActivityId);
  const readiness = (items: DocumentListItem[], selectedActivityId: string) => {
    const matching = items.filter((item) => item.activity_id === selectedActivityId);
    return { ready: matching.filter((item) => item.storage_key).length, total: matching.length };
  };

  return <section>
    <h1 className="text-3xl font-bold">Document operations</h1>
    <p className="mt-2 text-slate-600 dark:text-slate-400">Issue certificates for an eligible activity, prepare them before sharing, or revoke activity certificates at activity or student level.</p>
    <form onSubmit={submitIssue} className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-2">
      <select required value={activityId} onChange={(event) => setActivityId(event.target.value)} className="rounded border p-2"><option value="">Choose a READY or PUBLISHED activity</option>{issuableActivities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date} · {item.status}</option>)}</select>
      <button disabled={issue.isPending || !issuableActivities.length} className="rounded bg-slate-900 p-2 text-white disabled:cursor-not-allowed disabled:opacity-60">Issue certificates for eligible participants</button>
    </form>
    {activities.isSuccess && !issuableActivities.length && <p className="mt-2 text-sm text-slate-500">No activities are ready to issue. Mark an activity READY first.</p>}
    <section className="mt-4 rounded-xl border p-4">
      <h2 className="font-semibold">Prepare documents for publishing</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Renders five PDFs per batch and stores them before students download. Continue until the selected group shows no remaining documents.</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Participant certificates</h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Regular participant and appreciation certificates.</p>
          <div className="mt-3 grid gap-3">
            <select aria-label="Participant certificate activity" value={preGenerationActivityId} onChange={(event) => setPreGenerationActivityId(event.target.value)} className="rounded border p-2"><option value="">Choose a PUBLISHED activity</option>{publishedActivities.map((item) => { const count = readiness(activityCertificates, item.id); return <option key={item.id} value={item.id}>{item.name} · {item.activity_date} · {count.ready}/{count.total} ready</option>; })}</select>
            <button type="button" disabled={!preGenerationActivityId || preGenerate.isPending} onClick={() => preGenerate.mutate()} className="rounded bg-indigo-700 p-2 text-white disabled:opacity-60">{preGenerate.isPending ? "Preparing participant PDFs…" : "Prepare next 5 participant PDFs"}</button>
          </div>
          {preGenerate.data && <p role="status" className="mt-3 rounded bg-green-50 p-3 text-sm text-green-800">Ready: {preGenerate.data.ready_documents}/{preGenerate.data.total_documents}. Generated: {preGenerate.data.generated_documents}. Remaining: {preGenerate.data.remaining_documents}.{preGenerate.data.failed_document_ids.length ? ` Failed: ${preGenerate.data.failed_document_ids.length}. Click again to retry.` : ""}</p>}
        </div>
        <div className="rounded-lg border border-amber-200 p-4 dark:border-amber-900">
          <h3 className="font-semibold">Executive Council certificates</h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">EC organizer certificates use their assigned EC template and renderer.</p>
          <div className="mt-3 grid gap-3">
            <select aria-label="Executive Council certificate activity" value={ecPreGenerationActivityId} onChange={(event) => setEcPreGenerationActivityId(event.target.value)} className="rounded border p-2"><option value="">Choose an activity with issued EC certificates</option>{ecActivities.map((item) => { const count = readiness(ecCertificates, item.id); return <option key={item.id} value={item.id}>{item.name} · {item.activity_date} · {count.ready}/{count.total} ready</option>; })}</select>
            <button type="button" disabled={!ecPreGenerationActivityId || preGenerateEc.isPending} onClick={() => preGenerateEc.mutate()} className="rounded bg-amber-700 p-2 text-white disabled:opacity-60">{preGenerateEc.isPending ? "Preparing EC PDFs…" : "Prepare next 5 EC PDFs"}</button>
          </div>
          {preGenerateEc.data && <p role="status" className="mt-3 rounded bg-green-50 p-3 text-sm text-green-800">Ready: {preGenerateEc.data.ready_documents}/{preGenerateEc.data.total_documents}. Generated: {preGenerateEc.data.generated_documents}. Remaining: {preGenerateEc.data.remaining_documents}.{preGenerateEc.data.failed_document_ids.length ? ` Failed: ${preGenerateEc.data.failed_document_ids.length}. Click again to retry.` : ""}</p>}
          {documents.isSuccess && !ecActivities.length && <p className="mt-3 text-sm text-slate-500">No valid EC certificates have been issued yet.</p>}
        </div>
      </div>
    </section>
    <section className="mt-4 rounded-xl border border-red-200 p-4">
      <h2 className="font-semibold">Revoke activity certificates</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Revoke every valid certificate for an activity, or only the certificate belonging to one student. Revocations preserve the audit record and do not affect leadership documents.</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <select value={revokeActivityId} onChange={(event) => { setRevokeActivityId(event.target.value); setStudentDocumentId(""); }} className="rounded border p-2"><option value="">Choose an activity with valid certificates</option>{revocableActivities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date}</option>)}</select>
        <button type="button" disabled={!revokeActivityId || revokeActivity.isPending} onClick={() => { if (selectedActivity && window.confirm(`Revoke every valid certificate for ${selectedActivity.name}? This cannot be undone.`)) revokeActivity.mutate(); }} className="rounded border border-red-600 p-2 text-red-700 disabled:opacity-60">{revokeActivity.isPending ? "Revoking…" : "Revoke all activity certificates"}</button>
        <select value={studentDocumentId} onChange={(event) => setStudentDocumentId(event.target.value)} disabled={!revokeActivityId} className="rounded border p-2 disabled:opacity-60"><option value="">Choose one student certificate</option>{studentActivityDocuments.map((item) => <option key={item.id} value={item.id}>{item.roll_number} — {item.student_name}</option>)}</select>
        <button type="button" disabled={!studentDocumentId || revokeStudent.isPending} onClick={() => { const document = studentActivityDocuments.find((item) => item.id === studentDocumentId); if (document && window.confirm(`Revoke ${document.student_name}'s certificate for this activity? This cannot be undone.`)) revokeStudent.mutate(); }} className="rounded border border-red-600 p-2 text-red-700 disabled:opacity-60">{revokeStudent.isPending ? "Revoking…" : "Revoke selected student's certificate"}</button>
      </div>
    </section>
    <form onSubmit={(event) => submitDocument(event, "reissue")} className="mt-4 grid gap-3 rounded-xl border p-4 md:grid-cols-3">
      <select required value={documentId} onChange={(event) => setDocumentId(event.target.value)} className="rounded border p-2 md:col-span-1"><option value="">Choose an issued document</option>{operationalDocuments.map((item) => <option key={item.id} value={item.id}>{item.document_type} · {item.roll_number} · v{item.version} · {item.verification_id}</option>)}</select>
      <button disabled={!documentId || reissue.isPending} className="rounded border p-2">Reissue as new version</button>
      <button type="button" disabled={!documentId || revoke.isPending} onClick={() => revoke.mutate()} className="rounded border border-red-600 p-2 text-red-700">Revoke document</button>
    </form>
    {documents.error && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-red-700">{documents.error.message}</p>}
    {error && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {message && <p role="status" className="mt-4 rounded bg-green-50 p-3 text-green-800">{message}</p>}
  </section>;
}
