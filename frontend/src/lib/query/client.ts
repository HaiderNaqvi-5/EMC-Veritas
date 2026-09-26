import { MutationCache, QueryClient } from "@tanstack/react-query";
import { notifyAction } from "../feedback/actions";

const retrySafeGet = (failureCount: number, error: unknown) => {
  if (error instanceof Error && error.name === "AbortError") return false;
  return failureCount < 2;
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
      retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 4_000),
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
