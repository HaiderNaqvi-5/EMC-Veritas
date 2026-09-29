import { apiRequest } from "../../lib/api/client";

export type AdminRole = "ADMIN" | "SUPER_ADMIN";

export type AdminSession = { authenticated: boolean; role?: AdminRole; temporary_password_change_required?: boolean };

export const authApi = {
  // Login and all write actions deliberately remain single-attempt: retrying
  // them while the hosted API wakes could double-submit a state change.
  login: (rollNumber: string, password: string) => apiRequest<AdminSession>("/admin/auth/login", { method: "POST", body: JSON.stringify({ roll_number: rollNumber, password }) }),
  logout: () => apiRequest<void>("/admin/auth/logout", { method: "POST" }),
  currentSession: () => apiRequest<AdminSession>("/admin/auth/session"),
  changeTemporaryPassword: (currentPassword: string, newPassword: string) => apiRequest<void>("/admin/auth/change-temporary-password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
};
