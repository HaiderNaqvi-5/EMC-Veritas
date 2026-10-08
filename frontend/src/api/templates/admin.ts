import { apiBlobRequest, apiRequest, deleteApiResource, retryConnection } from "../../lib/api/client";

export type Template = {
  id: string;
  name: string;
  approved: boolean;
  archived: boolean;
  signature_handling: "retain" | "replace" | null;
  purpose: "PARTICIPANT" | "EXECUTIVE_COUNCIL";
  created_at: string;
};

export type TemplateField = {
  field_name: string;
  page_number: number;
  x: number;
  y: number;
  width: number;
  height: number;
  font_family?: "helv" | "tiro" | "cour" | "mont" | "custom";
  custom_font_id?: string | null;
  font_size?: number | null;
  text_color?: string;
};

export type TemplateFont = {
  id: string;
  name: string;
  content_type: "font/ttf" | "font/otf";
  created_at: string;
};

export type TemplateAnalysis = {
  page_count: number;
  extracted_text: string[];
  ocr_used: boolean;
  ocr_required: boolean;
  signature_content_detected: boolean;
  detected_fields: Array<TemplateField & { detected_text: string }>;
};

export const listTemplates = (purpose: Template["purpose"] = "PARTICIPANT") =>
  apiRequest<Template[]>(`/admin/templates?purpose=${purpose}`);
export const deleteTemplate = (templateId: string) =>
  deleteApiResource(`/admin/templates/${templateId}`);
export const listTemplateFields = (templateId: string) =>
  apiRequest<TemplateField[]>(`/admin/templates/${templateId}/fields`);
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
export const listTemplateFonts = (templateId: string) =>
  apiRequest<TemplateFont[]>(`/admin/templates/${templateId}/fonts`);

export async function uploadTemplateFont(templateId: string, file: File): Promise<TemplateFont> {
  const data = new FormData();
  data.set("file", file);
  return apiRequest<TemplateFont>(`/admin/templates/${templateId}/fonts/upload`, {
    method: "POST",
    body: data,
  });
}

export async function templateSource(templateId: string): Promise<Blob> {
  return retryConnection(() => apiBlobRequest(`/admin/templates/${templateId}/source`));
}

export async function templatePageImage(templateId: string, pageNumber: number): Promise<Blob> {
  return retryConnection(() => apiBlobRequest(`/admin/templates/${templateId}/pages/${pageNumber}`));
}

export async function uploadTemplate(name: string, file: File, purpose: Template["purpose"] = "PARTICIPANT"): Promise<Template> {
  const data = new FormData();
  data.set("name", name);
  data.set("file", file);
  data.set("purpose", purpose);
  return apiRequest<Template>("/admin/templates/upload", { method: "POST", body: data });
}

export async function previewTemplate(
  templateId: string,
  studentId: string,
  activityId: string,
): Promise<Blob> {
  // Preview is explicitly non-issuing and has no database side effect, so a
  // retry during a transient hosted-service wake-up is safe.
  return retryConnection(() => apiBlobRequest(`/admin/templates/${templateId}/preview`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, activity_id: activityId }),
  }));
}
