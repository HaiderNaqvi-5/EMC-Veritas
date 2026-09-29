import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ login: vi.fn(), getStudentDocuments: vi.fn() }));
vi.mock("../features/auth/contracts", () => ({ authApi: { login: mocks.login } }));
vi.mock("../api/documents/public", () => ({ getStudentDocuments: mocks.getStudentDocuments, documentDownloadUrl: (id: string) => `/download/${id}` }));
import { StudentPortal } from "./StudentPortal";

function renderPortal() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><StudentPortal /></MemoryRouter></QueryClientProvider>);
}

function submitRollNumber(rollNumber: string) {
  const input = screen.getByLabelText("Roll number");
  fireEvent.change(input, { target: { value: rollNumber } });
  const form = input.closest("form");
  if (!form) throw new Error("lookup form not found");
  fireEvent.click(within(form).getByRole("button", { name: "Find my record" }));
}

afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("submitting a roll number loads the student's documents without an admin lookup", async () => {
  mocks.getStudentDocuments.mockResolvedValueOnce({ full_name: "Student", activity_certificates: [], leadership_recognition: [] });
  renderPortal();
  submitRollNumber("22-cs-1");
  await waitFor(() => expect(mocks.getStudentDocuments).toHaveBeenCalledWith("22-CS-1"));
  expect(mocks.login).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog", { name: "Admin sign in" })).not.toBeInTheDocument();
  expect(await screen.findByText("Student")).toBeInTheDocument();
});

test("admin sign in opens a modal that logs in with roll number and password", async () => {
  mocks.login.mockResolvedValueOnce({ authenticated: true });
  renderPortal();
  fireEvent.click(screen.getByRole("button", { name: "Admin sign in" }));
  const dialog = await screen.findByRole("dialog", { name: "Admin sign in" });
  fireEvent.change(within(dialog).getByLabelText("Roll number"), { target: { value: "22-cs-9" } });
  fireEvent.change(within(dialog).getByLabelText("Password"), { target: { value: "s3cret" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(mocks.login).toHaveBeenCalledWith("22-CS-9", "s3cret"));
});
