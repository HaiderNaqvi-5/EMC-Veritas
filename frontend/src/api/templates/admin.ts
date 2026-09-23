import { apiBase, apiRequest } from "../../lib/api/client";

export type Template = {
  id: string;
  name: string;
  approved: boolean;
  archived: boolean;
  signature_handling: "retain" | "replace" | null;
  created_at: string;
};

export type TemplateField = {
  field_name: string;
  page_number: number;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type TemplateAnalysis = {
  page_count: number;
  extracted_text: string[];
  ocr_used: boolean;
  ocr_required: boolean;
  signature_content_detected: boolean;
};

export const listTemplates = () => apiRequest<Template[]>("/admin/templates");
export const analyzeTemplate = (templateId: string) =>
  apiRequest<TemplateAnalysis>(`/admin/templates/${templateId}/analysis`);
export const configureTemplate = (
  templateId: string,
  fields: TemplateField[],
  signatureHandling: "retain" | "replace",
) =>
  apiRequest<Template>(`/admin/templates/${templateId}/fields`, {
    method: "POST",
    body: JSON.stringify({ fields, signature_handling: signatureHandling }),
  });
export const approveTemplate = (templateId: string) =>
  apiRequest<Template>(`/admin/templates/${templateId}/approve`, { method: "POST" });

export async function uploadTemplate(name: string, file: File): Promise<Template> {
  const data = new FormData();
  data.set("name", name);
  data.set("file", file);
  return apiRequest<Template>("/admin/templates/upload", { method: "POST", body: data });
}

export async function previewTemplate(
  templateId: string,
  studentId: string,
  activityId: string,
): Promise<Blob> {
  const response = await fetch(`${apiBase}/admin/templates/${templateId}/preview`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, activity_id: activityId }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The preview could not be generated.");
  }
  return response.blob();
}
