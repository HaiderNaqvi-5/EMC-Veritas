import { apiRequest } from "../../lib/api/client";

export type AdminRole = "ADMIN" | "SUPER_ADMIN";

export type AdminLookup = { is_admin: boolean; active: boolean };
export type AdminSession = { authenticated: boolean; role?: AdminRole; temporary_password_change_required?: boolean };

export const authApi = {
  lookup: (rollNumber: string) => apiRequest<AdminLookup>("/admin/auth/lookup", { method: "POST", body: JSON.stringify({ roll_number: rollNumber }) }),
  login: (rollNumber: string, password: string) => apiRequest<AdminSession>("/admin/auth/login", { method: "POST", body: JSON.stringify({ roll_number: rollNumber, password }) }),
  logout: () => apiRequest<void>("/admin/auth/logout", { method: "POST" }),
  currentSession: () => apiRequest<AdminSession>("/admin/auth/session"),
  changeTemporaryPassword: (currentPassword: string, newPassword: string) => apiRequest<void>("/admin/auth/change-temporary-password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
};
