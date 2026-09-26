import { MutationCache, QueryClient } from "@tanstack/react-query";
import { notifyAction } from "../feedback/actions";
import { ApiError, isApiConnectionError } from "../api/client";

const retrySafeGet = (failureCount: number, error: unknown) => {
  if (error instanceof Error && error.name === "AbortError") return false;
  // A connection error has no HTTP response and is safe to retry. Give the
  // Render free service enough time to wake before the app gives up or logs a
  // user out. Do not retry validation, permission, or other normal API errors.
  if (isApiConnectionError(error)) return failureCount < 8;
  return error instanceof ApiError && error.status >= 500 && failureCount < 2;
};

export const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onSuccess: () => notifyAction("success", "Your action was completed successfully."),
    onError: (error) => notifyAction(
      "error",
      error instanceof Error ? error.message : "The action could not be completed. Please try again.",
    ),
  }),
  defaultOptions: {
    queries: {
      retry: retrySafeGet,
      retryDelay: (attempt) => Math.min(750 * 2 ** attempt, 10_000),
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
