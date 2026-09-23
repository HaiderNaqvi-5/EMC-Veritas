export const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";
export const SESSION_EXPIRED_EVENT = "emc:admin-session-expired";

export const apiUrl = (path: string) => `${apiBase}${path}`;

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    headers,
    ...init,
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/admin/auth/login") && !path.startsWith("/admin/auth/lookup")) {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? "The request could not be completed.");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function warmReadiness(): void {
  const controller = new AbortController();
  window.setTimeout(() => controller.abort(), 8_000);
  void fetch(`${apiBase}/health/ready`, { credentials: "include", signal: controller.signal }).catch(() => {
    // The visual shell remains usable while a free-tier backend wakes up.
  });
}
