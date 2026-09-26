export const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";
export const SESSION_EXPIRED_EVENT = "emc:admin-session-expired";

export const apiUrl = (path: string) => `${apiBase}${path}`;

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * A fetch rejection means that the browser never received an HTTP response.
 * This is distinct from a normal API validation/permission error and can occur
 * while the Render service is waking up or restarting.
 */
export class ApiConnectionError extends Error {
  constructor() {
    super(
      "Could not reach the EMC API. The service may be starting, unavailable, or its connection was interrupted. Please reload and try again.",
    );
    this.name = "ApiConnectionError";
  }
}

export const isApiConnectionError = (error: unknown): error is ApiConnectionError =>
  error instanceof ApiConnectionError;

const wait = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

/** Retry only connection failures for an operation that is safe to repeat. */
export async function retryConnection<T>(
  operation: () => Promise<T>,
  retries = 8,
): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      if (!isApiConnectionError(error) || attempt >= retries) throw error;
      // Covers a Render free-instance wake-up without retrying a real API error.
      await wait(Math.min(750 * 2 ** attempt, 10_000));
    }
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      credentials: "include",
      headers,
      ...init,
    });
  } catch {
    throw new ApiConnectionError();
  }
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
