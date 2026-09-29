import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ lookup: vi.fn(), getStudentDocuments: vi.fn() }));
vi.mock("../features/auth/contracts", () => ({ authApi: { lookup: mocks.lookup, login: vi.fn() } }));
vi.mock("../api/documents/public", () => ({ getStudentDocuments: mocks.getStudentDocuments, documentDownloadUrl: (id: string) => `/download/${id}` }));
import { StudentPortal } from "./StudentPortal";

function renderPortal() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><StudentPortal /></MemoryRouter></QueryClientProvider>);
}

function submitLookup(rollNumber: string) {
  const input = screen.getByLabelText("Roll number");
  fireEvent.change(input, { target: { value: rollNumber } });
  const form = input.closest("form");
  if (!form) throw new Error("lookup form not found");
  fireEvent.click(within(form).getByRole("button", { name: "Find my record" }));
}

afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("ordinary student lookup loads documents without showing an admin password modal", async () => {
  mocks.lookup.mockResolvedValueOnce({ is_admin: false, active: false });
  mocks.getStudentDocuments.mockResolvedValueOnce({ full_name: "Student", activity_certificates: [], leadership_recognition: [] });
  renderPortal();
  submitLookup("22-cs-1");
  await waitFor(() => expect(mocks.getStudentDocuments).toHaveBeenCalledWith("22-CS-1"));
  expect(screen.queryByRole("dialog", { name: "Admin sign in" })).not.toBeInTheDocument();
  expect(await screen.findByText("Student")).toBeInTheDocument();
});

test("recognized admin opens the password modal", async () => {
  mocks.lookup.mockResolvedValueOnce({ is_admin: true, active: true });
  renderPortal();
  submitLookup("22-cs-9");
  expect(await screen.findByText("Admin sign in")).toBeInTheDocument();
});
