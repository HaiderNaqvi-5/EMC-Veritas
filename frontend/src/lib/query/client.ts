import { QueryClient } from "@tanstack/react-query";

const retrySafeGet = (failureCount: number, error: unknown) => {
  if (error instanceof Error && error.name === "AbortError") return false;
  return failureCount < 2;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: retrySafeGet,
      retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 4_000),
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
