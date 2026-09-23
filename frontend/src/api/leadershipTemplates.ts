import { apiBase, apiRequest } from "../lib/api/client";

export type LeadershipTemplate = { id: string; name: string; role: string; document_type: "LEADERSHIP_RECOGNITION" | "END_OF_TENURE_APPRECIATION"; signature_handling: "retain" | "replace" | null; active: boolean; archived: boolean };
export type LeadershipField = { field_name: string; page_number: number; x: number; y: number; width: number; height: number };
export type ExecutiveMembership = { id: string; student_id: string; session_id: string; society_id: string | null; role: string; start_date: string; end_date: string | null; status: "ACTIVE" | "COMPLETED" | "REMOVED" };
export const listLeadershipTemplates = () => apiRequest<LeadershipTemplate[]>("/admin/leadership-templates");
export const listExecutiveMemberships = () => apiRequest<ExecutiveMembership[]>("/admin/executive-memberships");
export const activateLeadershipTemplate = (id: string) => apiRequest<LeadershipTemplate>(`/admin/leadership-templates/${id}/activate`, { method: "POST" });
export const deactivateLeadershipTemplate = (id: string) => apiRequest<LeadershipTemplate>(`/admin/leadership-templates/${id}/deactivate`, { method: "POST" });
export const archiveLeadershipTemplate = (id: string) => apiRequest<LeadershipTemplate>(`/admin/leadership-templates/${id}/archive`, { method: "POST" });
export const configureLeadershipTemplate = (id: string, fields: LeadershipField[], signature_handling: "retain" | "replace") => apiRequest<LeadershipTemplate>(`/admin/leadership-templates/${id}/fields`, { method: "POST", body: JSON.stringify({ fields, signature_handling }) });
export async function uploadLeadershipTemplate(name: string, role: string, document_type: LeadershipTemplate["document_type"], file: File) { const body = new FormData(); body.set("name", name); body.set("role", role); body.set("document_type", document_type); body.set("file", file); return apiRequest<LeadershipTemplate>("/admin/leadership-templates/upload", { method: "POST", body }); }
export async function previewLeadershipTemplate(id: string, membership_id: string): Promise<Blob> { const response = await fetch(`${apiBase}/admin/leadership-templates/${id}/preview`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ membership_id }) }); if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "The preview could not be generated."); } return response.blob(); }
