import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ apiRequest: vi.fn() }));
vi.mock("../../lib/api/client", () => ({ apiRequest: mocks.apiRequest }));
import { AdminDashboard } from "./AdminDashboard";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("shows privacy-preserving public usage totals", async () => {
  mocks.apiRequest.mockImplementation((path: string) => {
    if (path === "/admin/overview/public-usage") return Promise.resolve({ unique_record_viewers: 18, total_record_lookups: 42, unique_downloaders: 11, total_downloads: 27, tracking_started_at: "2026-10-11T00:00:00Z" });
    return Promise.resolve([]);
  });

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AdminDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Portal users")).toBeInTheDocument();
  expect(await screen.findByText("42 successful record lookups")).toBeInTheDocument();
  expect(screen.getByText("18")).toBeInTheDocument();
  expect(screen.getByText("Certificate downloaders")).toBeInTheDocument();
  expect(screen.getByText("11")).toBeInTheDocument();
  expect(screen.getByText("27 downloads started")).toBeInTheDocument();
});
