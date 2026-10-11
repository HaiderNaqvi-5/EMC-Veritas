import { apiRequest } from "../lib/api/client";

export type SupportCategory =
  | "MISSING_RECORD"
  | "MISSING_CERTIFICATE"
  | "INCORRECT_DETAILS"
  | "DOWNLOAD_PROBLEM"
  | "OTHER";

export type SupportRequestStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED";

export type SupportRequestCreate = {
  roll_number: string;
  full_name: string;
  contact_email: string;
  problem_category: SupportCategory;
  problem_details: string;
  website?: string;
};

export type SupportRequestCreated = {
  ticket_number: string;
  status: SupportRequestStatus;
};

export type SupportRequest = SupportRequestCreate & {
  id: string;
  ticket_number: string;
  status: SupportRequestStatus;
  admin_notes: string | null;
  resolution_message: string | null;
  resolved_by_admin_id: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export function createSupportRequest(payload: SupportRequestCreate) {
  return apiRequest<SupportRequestCreated>("/public/support-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listSupportRequests(status?: SupportRequestStatus, query?: string) {
  const search = new URLSearchParams();
  if (status) search.set("status", status);
  if (query?.trim()) search.set("query", query.trim());
  const suffix = search.size ? `?${search.toString()}` : "";
  return apiRequest<SupportRequest[]>(`/admin/support-requests${suffix}`);
}

export function updateSupportRequest(
  id: string,
  payload: Pick<SupportRequest, "status" | "admin_notes" | "resolution_message">,
) {
  return apiRequest<SupportRequest>(`/admin/support-requests/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export const supportCategoryLabels: Record<SupportCategory, string> = {
  MISSING_RECORD: "My record is missing",
  MISSING_CERTIFICATE: "A certificate is missing",
  INCORRECT_DETAILS: "My details are incorrect",
  DOWNLOAD_PROBLEM: "I cannot download a document",
  OTHER: "Something else",
};
