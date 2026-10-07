import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { activateLeadershipTemplate, analyzeLeadershipTemplate, assignLeadershipTemplate, configureLeadershipTemplate, deactivateLeadershipTemplate, deleteLeadershipTemplate, ExecutiveMembership, issueLeadershipLetter, LeadershipField, leadershipTemplatePageImage, listExecutiveMemberships, listLeadershipTemplates, previewLeadershipTemplate, uploadLeadershipTemplate } from "../../api/leadershipTemplates";
import { Skeleton } from "../../components/ui/Skeleton";

const baseRequiredNames = ["student_name", "roll_number", "role", "role_start_date", "role_end_date", "session_name", "issue_date", "verification_id", "qr_code"];
const requiredNamesForRole = (role?: string) => role === "Society Head" ? [...baseRequiredNames, "society_name"] : baseRequiredNames;
const membershipLabel = (item: ExecutiveMembership) => `${item.student_name} (${item.roll_number}) — ${item.role}${item.society_name ? ` · ${item.society_name}` : ""} · ${item.session_name}`;

export function LeadershipTemplatesPage() {
  const cache = useQueryClient();
  const templates = useQuery({ queryKey: ["admin", "leadership-templates"], queryFn: listLeadershipTemplates });
  const memberships = useQuery({ queryKey: ["admin", "executive-memberships"], queryFn: listExecutiveMemberships });
  const [name, setName] = useState("");
  const [uploadMembershipId, setUploadMembershipId] = useState("");
  const [type, setType] = useState<"LEADERSHIP_RECOGNITION" | "END_OF_TENURE_APPRECIATION">("LEADERSHIP_RECOGNITION");
  const [file, setFile] = useState<File | null>(null);
  const [selected, setSelected] = useState("");
  const [membershipId, setMembershipId] = useState("");
  const [signatureHandling, setSignatureHandling] = useState<"retain" | "replace">("retain");
  const [previewUrl, setPreviewUrl] = useState("");
  const [pageUrl, setPageUrl] = useState("");
  const current = templates.data?.find((template) => template.id === selected);
  const uploadMembership = memberships.data?.find((item) => item.id === uploadMembershipId);
  const templateMembership = memberships.data?.find((item) => item.id === current?.executive_membership_id);
  const analysis = useQuery({ queryKey: ["leadership-template-analysis", selected], queryFn: () => analyzeLeadershipTemplate(selected), enabled: Boolean(selected) });
  const sourcePage = useQuery({ queryKey: ["leadership-template-page", selected], queryFn: () => leadershipTemplatePageImage(selected, 1), enabled: Boolean(selected) });

  useEffect(() => { if (!sourcePage.data) { setPageUrl(""); return; } const url = URL.createObjectURL(sourcePage.data); setPageUrl(url); return () => URL.revokeObjectURL(url); }, [sourcePage.data]);
  useEffect(() => { setMembershipId(current?.executive_membership_id ?? ""); }, [current?.executive_membership_id]);
  const detected = analysis.data?.detected_fields ?? [];
  const detectedByName = new Map(detected.map((field) => [field.field_name, field]));
  const requiredNames = requiredNamesForRole(current?.role);
  const fallbackFields: LeadershipField[] = requiredNames.map((field_name, index) => ({ field_name, page_number: 1, x: 80, y: 100 + index * 32, width: field_name === "qr_code" ? 96 : 260, height: field_name === "qr_code" ? 96 : 24 }));
  const configuredFields = requiredNames.map((field_name) => detectedByName.get(field_name) ?? fallbackFields.find((field) => field.field_name === field_name) as LeadershipField);
  for (const field of detected) if (field.field_name.startsWith("signature_") && !configuredFields.some((item) => item.field_name === field.field_name)) configuredFields.push(field);
  const hasSignatureBoxes = configuredFields.some((field) => field.field_name.startsWith("signature_"));
  const effectiveHandling = hasSignatureBoxes ? "replace" : signatureHandling;
  const missingTags = requiredNames.filter((field_name) => !detectedByName.has(field_name));
  const refresh = () => cache.invalidateQueries({ queryKey: ["admin", "leadership-templates"] });
  const upload = useMutation({ mutationFn: () => uploadLeadershipTemplate(name, uploadMembership?.role ?? "", uploadMembershipId, type, file as File), onSuccess: (template) => { setSelected(template.id); setName(""); setFile(null); void refresh(); } });
  const configure = useMutation({ mutationFn: () => configureLeadershipTemplate(selected, configuredFields, effectiveHandling), onSuccess: () => void refresh() });
  const activate = useMutation({ mutationFn: activateLeadershipTemplate, onSuccess: () => void refresh() });
  const deactivate = useMutation({ mutationFn: deactivateLeadershipTemplate, onSuccess: () => void refresh() });
  const remove = useMutation({ mutationFn: deleteLeadershipTemplate, onSuccess: () => { setSelected(""); setPreviewUrl(""); void refresh(); } });
  const preview = useMutation({ mutationFn: () => previewLeadershipTemplate(selected, membershipId), onSuccess: (blob) => { if (previewUrl) URL.revokeObjectURL(previewUrl); setPreviewUrl(URL.createObjectURL(blob)); } });
  const assign = useMutation({ mutationFn: () => assignLeadershipTemplate(selected, membershipId), onSuccess: () => void refresh() });
  const issue = useMutation({ mutationFn: () => issueLeadershipLetter(selected), onSuccess: () => void cache.invalidateQueries({ queryKey: ["admin", "documents"] }) });
  useEffect(() => {
    preview.reset();
    issue.reset();
    configure.reset();
    activate.reset();
    deactivate.reset();
    assign.reset();
  }, [selected]);
  const error = [upload.error, analysis.error, sourcePage.error, configure.error, activate.error, deactivate.error, remove.error, preview.error, assign.error, issue.error].find(Boolean);
  const roleMemberships = memberships.data?.filter((item) => item.role === current?.role) ?? [];
  function submit(event: FormEvent) { event.preventDefault(); if (file && uploadMembership) upload.mutate(); }

  return <section className="space-y-6">
    <div><h1 className="text-3xl font-bold">Leadership templates</h1><p className="mt-2 text-slate-600 dark:text-slate-400">Assign each customized letter to the exact Executive Council appointment it belongs to.</p></div>
    <form onSubmit={submit} className="grid gap-3 rounded-xl border p-4 md:grid-cols-2 xl:grid-cols-6">
      <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Template name" className="rounded border p-2 xl:col-span-2"/>
      <select required value={uploadMembershipId} onChange={(event) => setUploadMembershipId(event.target.value)} className="rounded border p-2 xl:col-span-2" aria-label="Template recipient"><option value="">Choose the letter recipient</option>{memberships.data?.map((item) => <option key={item.id} value={item.id}>{membershipLabel(item)}</option>)}</select>
      <select value={type} onChange={(event) => setType(event.target.value as typeof type)} className="rounded border p-2"><option value="LEADERSHIP_RECOGNITION">Letter of Recognition</option><option value="END_OF_TENURE_APPRECIATION">End-of-Tenure Appreciation</option></select>
      <input required type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="rounded border p-2"/>
      <button disabled={!file || !uploadMembership || upload.isPending} className="rounded bg-slate-900 p-2 text-white xl:col-start-6">Upload for this member</button>
    </form>
    <label className="block max-w-3xl">Template<select value={selected} onChange={(event) => setSelected(event.target.value)} className="mt-1 block w-full rounded border p-2"><option value="">Choose a template</option>{templates.data?.map((template) => { const owner = memberships.data?.find((item) => item.id === template.executive_membership_id); return <option key={template.id} value={template.id}>{owner ? membershipLabel(owner) : `${template.role} — role-wide fallback`} — {template.name}{template.active ? " (active)" : ""}</option>; })}</select></label>
    {current && <>
      <div className="space-y-4 rounded-xl border p-4">
        <div><p><strong>{current.role}</strong> · {current.document_type === "LEADERSHIP_RECOGNITION" ? "Letter of Recognition" : "End-of-Tenure Appreciation"}</p><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Assigned to: {templateMembership ? membershipLabel(templateMembership) : `all ${current.role} appointments without a personal template`}</p></div>
        <p className="text-sm text-slate-600 dark:text-slate-400">{analysis.isError ? "Analysis failed. Reload after the backend update." : `Detected: ${detected.length ? detected.map((field) => field.field_name).join(", ") : "Analysing…"}`}</p>
        {missingTags.length > 0 && !analysis.isLoading && !analysis.isError && <p role="alert" className="rounded bg-amber-100 p-3 text-sm text-amber-900">Not detected: {missingTags.join(", ")}. Add these exact tags before activation.</p>}
        <div className="flex flex-wrap gap-3"><select value={effectiveHandling} disabled={hasSignatureBoxes} onChange={(event) => setSignatureHandling(event.target.value as "retain" | "replace")} className="rounded border p-2"><option value="retain">Retain sample signatures</option><option value="replace">Replace with configured signatories</option></select><button disabled={current.active || configure.isPending || analysis.isLoading || analysis.isError || missingTags.length > 0} onClick={() => configure.mutate()} className="rounded border px-3 py-2">Use detected field locations</button>{current.active ? <button disabled={deactivate.isPending} onClick={() => deactivate.mutate(current.id)} className="rounded border px-3 py-2">Deactivate</button> : <button disabled={!current.signature_handling || activate.isPending} onClick={() => activate.mutate(current.id)} className="rounded bg-emerald-700 px-3 py-2 font-semibold text-white">Activate for this member</button>}{current.active && current.executive_membership_id && <button disabled={issue.isPending} onClick={() => { if (window.confirm(`Issue ${current.document_type === "LEADERSHIP_RECOGNITION" ? "the Letter of Recognition" : "the End-of-Tenure Appreciation letter"} from this template now? If this member already has a valid letter of this type, the old PDF will be preserved in the audit history and marked superseded.`)) issue.mutate(); }} className="rounded bg-amber-600 px-3 py-2 font-semibold text-white">{issue.isPending ? "Preparing official letter…" : "Issue or replace official letter"}</button>}<button disabled={remove.isPending} onClick={() => { if (window.confirm(`Delete ${current.name}? It will be removed from this list.`)) remove.mutate(current.id); }} className="rounded border border-red-600 px-3 py-2 text-red-700 disabled:opacity-60">Delete template</button></div>
        {issue.data && <p role="status" className="rounded bg-emerald-100 p-3 text-sm text-emerald-900">{issue.data.superseded_document_id ? "Corrected letter issued; the previous version remains preserved as superseded." : "Official letter issued."} Version: <strong>{issue.data.version}</strong>. Verification ID: <strong>{issue.data.verification_id}</strong>. It is now available in Documents and through the student's roll-number lookup.</p>}
      </div>
      <section className="space-y-3 rounded-xl border p-4"><div><h2 className="text-xl font-semibold">Visual field placement</h2><p className="text-sm text-slate-600 dark:text-slate-400">Blue boxes show the exact PDF positions that will be saved.</p></div>{pageUrl ? <div className="relative w-fit max-w-full overflow-auto border"><img src={pageUrl} alt="Leadership template page 1" className="block max-w-none"/>{configuredFields.map((field) => <div key={field.field_name} className="absolute border-2 border-indigo-600 bg-indigo-300/20 text-xs" style={{ left: `${field.x / 842 * 100}%`, top: `${field.y / 596 * 100}%`, width: `${field.width / 842 * 100}%`, height: `${field.height / 596 * 100}%` }}><span className="bg-indigo-700 px-1 text-white">{field.field_name}</span></div>)}</div> : <Skeleton className="h-[600px] w-full"/>}</section>
      <div className="flex flex-wrap gap-3 rounded-xl border p-4"><select value={membershipId} disabled={Boolean(current.executive_membership_id)} onChange={(event) => setMembershipId(event.target.value)} className="min-w-72 rounded border p-2"><option value="">Choose an Executive membership</option>{roleMemberships.map((item) => <option key={item.id} value={item.id}>{membershipLabel(item)}</option>)}</select>{!current.executive_membership_id && <button disabled={!membershipId || assign.isPending} onClick={() => assign.mutate()} className="rounded bg-indigo-700 px-3 py-2 font-semibold text-white">Assign this template to member</button>}<button disabled={!membershipId || preview.isPending} onClick={() => preview.mutate()} className="rounded border px-3 py-2">Generate substituted preview</button></div>
    </>}
    {previewUrl && <iframe title="Leadership preview" src={previewUrl} className="h-[680px] w-full rounded-xl border"/>}
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error.message}</p>}
  </section>;
}
