import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeTemplate,
  approveTemplate,
  configureTemplate,
  listTemplates,
  previewTemplate,
  TemplateField,
  uploadTemplate,
} from "../../api/templates/admin";
import { Skeleton } from "../../components/ui/Skeleton";

const requiredFields: TemplateField[] = [
  "student_name",
  "roll_number",
  "activity_name",
  "activity_date",
].map((field_name, index) => ({
  field_name,
  page_number: 1,
  x: 100,
  y: 160 + index * 55,
  width: 300,
  height: 30,
}));

export function TemplateEditorPage() {
  const queryClient = useQueryClient();
  const templates = useQuery({ queryKey: ["admin", "templates"], queryFn: listTemplates });
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [handling, setHandling] = useState<"retain" | "replace">("retain");
  const [fields, setFields] = useState<TemplateField[]>(requiredFields);
  const [studentId, setStudentId] = useState("");
  const [activityId, setActivityId] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "templates"] });
  const upload = useMutation({
    mutationFn: () => uploadTemplate(name, file as File),
    onSuccess: (template) => { setSelectedId(template.id); setName(""); setFile(null); void refresh(); },
  });
  const analysis = useQuery({ queryKey: ["template-analysis", selectedId], queryFn: () => analyzeTemplate(selectedId), enabled: Boolean(selectedId) });
  const configure = useMutation({ mutationFn: () => configureTemplate(selectedId, fields, handling), onSuccess: () => void refresh() });
  const approve = useMutation({ mutationFn: () => approveTemplate(selectedId), onSuccess: () => void refresh() });
  const preview = useMutation({
    mutationFn: () => previewTemplate(selectedId, studentId, activityId),
    onSuccess: (blob) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(blob));
    },
  });
  const error = [upload.error, analysis.error, configure.error, approve.error, preview.error].find(Boolean);
  const selected = templates.data?.find((template) => template.id === selectedId);

  function submitUpload(event: FormEvent) { event.preventDefault(); if (file) upload.mutate(); }
  function updateField(index: number, key: keyof TemplateField, value: string) {
    setFields((current) => current.map((field, fieldIndex) => fieldIndex === index ? { ...field, [key]: key === "field_name" ? value : Number(value) } : field));
  }
  function addField() { setFields((current) => [...current, { field_name: "", page_number: 1, x: 100, y: 100, width: 180, height: 40 }]); }

  return <section className="space-y-6"><div><h1 className="text-3xl font-bold">Certificate templates</h1><p className="mt-2 text-slate-600 dark:text-slate-400">Upload a PDF, confirm its dynamic field placements, choose how sample signatures are handled, and approve only after review.</p></div>
    <form onSubmit={submitUpload} className="grid gap-3 rounded-xl border p-4 md:grid-cols-3"><input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Template name" className="rounded border p-2"/><input required accept="application/pdf" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="rounded border p-2"/><button disabled={!file || upload.isPending} className="rounded bg-slate-900 p-2 text-white">Upload PDF</button></form>
    {templates.isLoading ? <Skeleton className="h-20 w-full"/> : <label className="block max-w-xl text-sm font-medium">Template<select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="mt-1 block w-full rounded border p-2"><option value="">Choose a template</option>{templates.data?.map((template) => <option key={template.id} value={template.id}>{template.name}{template.approved ? " — approved" : ""}</option>)}</select></label>}
    {selectedId && <div className="grid gap-6 lg:grid-cols-2"><div className="space-y-4 rounded-xl border p-4"><h2 className="text-xl font-semibold">Analysis</h2>{analysis.isLoading ? <Skeleton className="h-36 w-full"/> : analysis.data && <><p>{analysis.data.page_count} page(s). {analysis.data.ocr_used ? "OCR was used for scanned pages." : "Embedded PDF text was used."}</p>{analysis.data.ocr_required && <p role="alert" className="rounded bg-amber-100 p-3 text-amber-900">Some pages still need manual attention before field placement.</p>}{analysis.data.signature_content_detected && <p role="alert" className="rounded bg-amber-100 p-3 text-amber-900">Signature or date content was detected. Choose retain or replace explicitly below.</p>}<pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-100 p-3 text-xs dark:bg-slate-800">{analysis.data.extracted_text.join("\n\n") || "No readable text found."}</pre></>}</div>
      <form onSubmit={(event) => { event.preventDefault(); configure.mutate(); }} className="space-y-4 rounded-xl border p-4"><h2 className="text-xl font-semibold">Field configuration</h2><label className="block text-sm">Signature handling<select value={handling} onChange={(event) => setHandling(event.target.value as "retain" | "replace")} className="mt-1 block w-full rounded border p-2"><option value="retain">Retain existing sample signatures</option><option value="replace">Replace with configured signatories</option></select></label>{fields.map((field, index) => <div key={`${field.field_name}-${index}`} className="grid grid-cols-2 gap-2 md:grid-cols-3"><input required value={field.field_name} onChange={(event) => updateField(index, "field_name", event.target.value)} className="rounded border p-2"/>{(["page_number", "x", "y", "width", "height"] as const).map((key) => <input key={key} required type="number" min={key === "page_number" ? 1 : 0} value={field[key]} onChange={(event) => updateField(index, key, event.target.value)} aria-label={`${field.field_name} ${key}`} className="rounded border p-2"/>)}</div>)}<button type="button" onClick={addField} className="rounded border px-3 py-2">Add field</button>{handling === "replace" && <p className="text-sm text-slate-600 dark:text-slate-400">Add `signature_president` and `signature_dsa` fields for ordinary activity certificates.</p>}<button disabled={configure.isPending || selected?.approved} className="rounded bg-indigo-600 px-4 py-2 text-white">Save immutable field configuration</button></form></div>}
    {selectedId && <div className="flex flex-wrap gap-3 rounded-xl border p-4"><button disabled={approve.isPending || selected?.approved} onClick={() => approve.mutate()} className="rounded bg-emerald-700 px-4 py-2 text-white">Approve template</button><input value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="Preview student ID" className="rounded border p-2"/><input value={activityId} onChange={(event) => setActivityId(event.target.value)} placeholder="Preview activity ID" className="rounded border p-2"/><button disabled={!studentId || !activityId || preview.isPending} onClick={() => preview.mutate()} className="rounded border px-4 py-2">Generate watermarked preview</button></div>}
    {previewUrl && <iframe title="Watermarked certificate preview" src={previewUrl} className="h-[680px] w-full rounded-xl border"/>}{error && <p role="alert" className="text-red-700">{error.message}</p>}</section>;
}
