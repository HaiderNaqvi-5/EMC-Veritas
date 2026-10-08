import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../lib/api/client";

type IssueResult = { issue_date: string; issued_document_ids: string[]; skipped_student_ids: string[] };
type ReissueResult = { replacement_document_id: string; issue_date: string; version: number };
type PreGenerationResult = { total_documents: number; ready_documents: number; generated_documents: number; remaining_documents: number; failed_document_ids: string[] };
type ActivityRevokeResult = { activity_id: string; student_id: string | null; revoked_document_ids: string[] };
type DocumentPurgeResult = { scope: string; activity_id: string | null; student_id: string | null; deleted_document_ids: string[] };
type DocumentListItem = {
  id: string; student_id: string; student_name: string; roll_number: string; activity_id: string | null;
  document_type: string; verification_id: string; issue_date: string; status: string; version: number;
};
type Activity = { id: string; name: string; activity_date: string; status: string };

export function DocumentsPage({ role }: { role: "ADMIN" | "SUPER_ADMIN" }) {
  const client = useQueryClient();
  const [activityId, setActivityId] = useState("");
  const [preGenerationActivityId, setPreGenerationActivityId] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [revokeActivityId, setRevokeActivityId] = useState("");
  const [studentDocumentId, setStudentDocumentId] = useState("");
  const [purgeActivityId, setPurgeActivityId] = useState("");
  const [purgeStudentId, setPurgeStudentId] = useState("");
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
  const revocableActivities = useMemo(() => {
    const ids = new Set(activityCertificates.map((item) => item.activity_id));
    return (activities.data ?? []).filter((item) => ids.has(item.id));
  }, [activities.data, activityCertificates]);
  const studentActivityDocuments = useMemo(
    () => activityCertificates.filter((item) => item.activity_id === revokeActivityId),
    [activityCertificates, revokeActivityId],
  );
  const allActivityCertificates = useMemo(
    () => (documents.data ?? []).filter((item) => item.document_type === "ACTIVITY_CERTIFICATE" && item.activity_id),
    [documents.data],
  );
  const purgeableActivities = useMemo(() => {
    const ids = new Set(allActivityCertificates.map((item) => item.activity_id));
    return (activities.data ?? []).filter((item) => ids.has(item.id));
  }, [activities.data, allActivityCertificates]);
  const purgeableStudents = useMemo(() => {
    const entries = allActivityCertificates.filter((item) => item.activity_id === purgeActivityId);
    return Array.from(new Map(entries.map((item) => [item.student_id, item])).values());
  }, [allActivityCertificates, purgeActivityId]);
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
  const purgeActivity = useMutation({
    mutationFn: () => apiRequest<DocumentPurgeResult>(`/admin/documents/activities/${purgeActivityId}/documents`, { method: "DELETE" }),
    onSuccess: (result) => { setMessage(`Permanently deleted ${result.deleted_document_ids.length} activity certificate record(s) and file(s).`); setPurgeStudentId(""); refreshDocuments(); },
  });
  const purgeStudent = useMutation({
    mutationFn: () => apiRequest<DocumentPurgeResult>(`/admin/documents/students/${purgeStudentId}/documents`, { method: "DELETE" }),
    onSuccess: (result) => { setMessage(`Permanently deleted ${result.deleted_document_ids.length} document record(s) for this student, including leadership documents.`); setPurgeStudentId(""); refreshDocuments(); },
  });
  function submitIssue(event: FormEvent) { event.preventDefault(); setMessage(""); issue.mutate(); }
  function submitDocument(event: FormEvent, action: "revoke" | "reissue") { event.preventDefault(); setMessage(""); if (action === "revoke") revoke.mutate(); else reissue.mutate(); }
  const error = issue.error?.message ?? preGenerate.error?.message ?? revoke.error?.message ?? revokeActivity.error?.message ?? revokeStudent.error?.message ?? purgeActivity.error?.message ?? purgeStudent.error?.message ?? reissue.error?.message ?? activities.error?.message;
  const readyActivities = activities.data?.filter((item) => item.status === "READY") ?? [];
  const publishedActivities = activities.data?.filter((item) => item.status === "PUBLISHED") ?? [];
  const selectedActivity = revocableActivities.find((item) => item.id === revokeActivityId);

  return <section>
    <h1 className="text-3xl font-bold">Document operations</h1>
    <p className="mt-2 text-slate-600 dark:text-slate-400">Issue certificates for an eligible activity, prepare them before sharing, or revoke activity certificates at activity or student level.</p>
    <form onSubmit={submitIssue} className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-2">
      <select required value={activityId} onChange={(event) => setActivityId(event.target.value)} className="rounded border p-2"><option value="">Choose a READY activity</option>{readyActivities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date}</option>)}</select>
      <button disabled={issue.isPending || !readyActivities.length} className="rounded bg-slate-900 p-2 text-white disabled:cursor-not-allowed disabled:opacity-60">Issue eligible certificates</button>
    </form>
    {activities.isSuccess && !readyActivities.length && <p className="mt-2 text-sm text-slate-500">No activities are ready to issue. Mark an activity READY first.</p>}
    <section className="mt-4 rounded-xl border p-4">
      <h2 className="font-semibold">Prepare certificates for sharing</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Renders five certificates at a time and saves them before students download.</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <select value={preGenerationActivityId} onChange={(event) => setPreGenerationActivityId(event.target.value)} className="rounded border p-2"><option value="">Choose a PUBLISHED activity</option>{publishedActivities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date}</option>)}</select>
        <button disabled={!preGenerationActivityId || preGenerate.isPending} onClick={() => preGenerate.mutate()} className="rounded bg-indigo-700 p-2 text-white disabled:opacity-60">{preGenerate.isPending ? "Preparing…" : "Prepare next 5 certificates"}</button>
      </div>
      {preGenerate.data && <p role="status" className="mt-3 rounded bg-green-50 p-3 text-sm text-green-800">Ready: {preGenerate.data.ready_documents}/{preGenerate.data.total_documents}. Generated in this batch: {preGenerate.data.generated_documents}. Remaining: {preGenerate.data.remaining_documents}.{preGenerate.data.failed_document_ids.length ? ` Failed: ${preGenerate.data.failed_document_ids.length}. Click again to retry.` : ""}</p>}
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
    {role === "SUPER_ADMIN" && <section className="mt-4 rounded-xl border-2 border-red-700 bg-red-50 p-4 dark:bg-red-950/20">
      <h2 className="font-semibold text-red-800 dark:text-red-200">Permanent document deletion</h2>
      <p className="mt-1 text-sm text-red-800 dark:text-red-200">This irreversibly removes records and generated files. It includes already revoked documents. Activity deletion removes all certificates for that activity; student deletion removes that student's activity certificates and leadership letters across the system.</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <select value={purgeActivityId} onChange={(event) => { setPurgeActivityId(event.target.value); setPurgeStudentId(""); }} className="rounded border p-2"><option value="">Choose an activity with certificates</option>{purgeableActivities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date}</option>)}</select>
        <button type="button" disabled={!purgeActivityId || purgeActivity.isPending} onClick={() => { const activity = purgeableActivities.find((item) => item.id === purgeActivityId); if (activity && window.confirm(`Permanently delete every certificate for ${activity.name}? This cannot be undone.`)) purgeActivity.mutate(); }} className="rounded border border-red-700 bg-red-700 p-2 text-white disabled:opacity-60">{purgeActivity.isPending ? "Deleting…" : "Delete all activity certificates permanently"}</button>
        <select value={purgeStudentId} onChange={(event) => setPurgeStudentId(event.target.value)} disabled={!purgeActivityId} className="rounded border p-2 disabled:opacity-60"><option value="">Choose a student from this activity</option>{purgeableStudents.map((item) => <option key={item.student_id} value={item.student_id}>{item.roll_number} — {item.student_name}</option>)}</select>
        <button type="button" disabled={!purgeStudentId || purgeStudent.isPending} onClick={() => { const student = purgeableStudents.find((item) => item.student_id === purgeStudentId); if (student && window.confirm(`Permanently delete every document for ${student.student_name}, including leadership letters? This cannot be undone.`)) purgeStudent.mutate(); }} className="rounded border border-red-700 p-2 text-red-800 disabled:opacity-60 dark:text-red-200">{purgeStudent.isPending ? "Deleting…" : "Delete this student's documents permanently"}</button>
      </div>
    </section>}
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
