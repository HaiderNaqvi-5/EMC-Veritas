import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listTemplates } from "../../api/templates/admin";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";
import { TemplateEditorPage } from "../templates/TemplateEditorPage";

type Activity = { id: string; session_id: string; name: string; activity_date: string; status: string };
type Member = { membership_id: string; student_id: string; roll_number: string; full_name: string; role: string; selected: boolean };
type IssueResult = { issued: number; newly_issued: number; reissued: number; document_ids: string[]; superseded_document_ids: string[] };

export function ExecutiveCouncilCertificatesPage() {
  const client = useQueryClient();
  const [activityId, setActivityId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [rosterDirty, setRosterDirty] = useState(false);
  const activities = useQuery({ queryKey: ["admin", "ec-certificates", "activities"], queryFn: () => apiRequest<Activity[]>("/admin/ec-certificates/activities") });
  const templates = useQuery({ queryKey: ["admin", "templates", "EXECUTIVE_COUNCIL"], queryFn: () => listTemplates("EXECUTIVE_COUNCIL") });
  const members = useQuery({ queryKey: ["admin", "ec-certificates", activityId, "members"], queryFn: () => apiRequest<Member[]>(`/admin/ec-certificates/activities/${activityId}/members`), enabled: Boolean(activityId) });

  useEffect(() => {
    setSelectedIds(new Set(members.data?.filter((item) => item.selected).map((item) => item.membership_id) ?? []));
    setRosterDirty(false);
  }, [members.data]);

  const save = useMutation({
    mutationFn: () => apiRequest<Member[]>(`/admin/ec-certificates/activities/${activityId}/members`, { method: "PUT", body: JSON.stringify({ membership_ids: [...selectedIds] }) }),
    onSuccess: () => { setRosterDirty(false); void client.invalidateQueries({ queryKey: ["admin", "ec-certificates", activityId, "members"] }); },
  });
  const issue = useMutation({
    mutationFn: () => apiRequest<IssueResult>(`/admin/ec-certificates/activities/${activityId}/issue`, { method: "POST", body: JSON.stringify({ template_id: templateId }) }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin", "documents"] }),
  });
  const approvedTemplates = templates.data?.filter((item) => item.approved) ?? [];
  const error = activities.error?.message ?? templates.error?.message ?? members.error?.message ?? save.error?.message ?? issue.error?.message;

  return <div className="space-y-10">
    <TemplateEditorPage purpose="EXECUTIVE_COUNCIL" />
    <section className="space-y-5 border-t pt-8">
      <div><h2 className="text-2xl font-bold">Issue EC organizer certificates</h2><p className="mt-2 text-slate-600 dark:text-slate-400">Choose an activity, select only the Executive Council members who organized it, save the roster, then issue certificates using an approved EC template.</p></div>
      <div className="grid gap-3 rounded-xl border p-4 md:grid-cols-2">
        <label className="text-sm font-medium">Activity<select value={activityId} onChange={(event) => { setActivityId(event.target.value); setRosterDirty(false); issue.reset(); }} className="mt-1 block w-full rounded border p-2"><option value="">Choose an activity</option>{activities.data?.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.activity_date} · {item.status}</option>)}</select></label>
        <label className="text-sm font-medium">Approved EC template<select value={templateId} onChange={(event) => setTemplateId(event.target.value)} className="mt-1 block w-full rounded border p-2"><option value="">Choose an approved EC template</option>{approvedTemplates.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </div>
      {activityId && (members.isLoading ? <Skeleton className="h-56 w-full"/> : <div className="overflow-x-auto rounded-xl border"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="p-3">Organizer</th><th className="p-3">Roll number</th><th className="p-3">EC role</th><th className="p-3">Include</th></tr></thead><tbody>{members.data?.map((member) => <tr key={member.membership_id} className="border-b last:border-0"><td className="p-3">{member.full_name}</td><td className="p-3">{member.roll_number}</td><td className="p-3">{member.role}</td><td className="p-3"><input type="checkbox" aria-label={`Include ${member.full_name}`} checked={selectedIds.has(member.membership_id)} onChange={(event) => { setRosterDirty(true); setSelectedIds((current) => { const next = new Set(current); if (event.target.checked) next.add(member.membership_id); else next.delete(member.membership_id); return next; }); }}/></td></tr>)}</tbody></table>{!members.data?.length && <p className="p-4 text-sm text-amber-700">No active or completed EC memberships exist for this activity’s session.</p>}</div>)}
      {activityId && <div className="flex flex-wrap items-center gap-3"><button disabled={save.isPending || !rosterDirty} onClick={() => save.mutate()} className="rounded border px-4 py-2 font-semibold disabled:opacity-50">{save.isPending ? "Saving roster…" : "Save organizer roster"}</button><button disabled={!templateId || !selectedIds.size || rosterDirty || save.isPending || issue.isPending} onClick={() => { if (window.confirm(`Publish EC organizer certificates for ${selectedIds.size} selected member(s)? Anyone who already has a valid certificate for this activity will receive a new version from the selected template. Their previous version will remain in the audit history as superseded.`)) issue.mutate(); }} className="rounded bg-amber-600 px-4 py-2 font-semibold text-white disabled:opacity-50">{issue.isPending ? "Preparing certificates…" : "Publish or replace EC certificates"}</button>{rosterDirty && <span className="text-sm text-amber-700">Save the changed roster before issuing.</span>}</div>}
      {save.isSuccess && <p role="status" className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">Organizer roster saved.</p>}
      {issue.data && <p role="status" className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">Published {issue.data.issued} EC certificate(s): {issue.data.newly_issued} new and {issue.data.reissued} replacement(s). Previous versions remain preserved in the audit history.</p>}
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    </section>
  </div>;
}
