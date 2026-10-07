import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ getStudentDocuments: vi.fn(), downloadDocument: vi.fn() }));
vi.mock("../api/documents/public", () => ({ getStudentDocuments: mocks.getStudentDocuments, downloadDocument: mocks.downloadDocument }));
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
  expect(screen.queryByText("Admin sign in")).not.toBeInTheDocument();
  expect(screen.queryByText("Student sign in")).not.toBeInTheDocument();
  expect(await screen.findByText("Student")).toBeInTheDocument();
});

test("downloads an issued leadership document with explicit progress", async () => {
  const createObjectURL = vi.fn(() => "blob:certificate");
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
  mocks.getStudentDocuments.mockResolvedValueOnce({
    full_name: "Student",
    activity_certificates: [],
    leadership_recognition: [{ id: "document-1", title: "Leadership Recognition", issue_date: "2026-10-08", status: "VALID" }],
  });
  mocks.downloadDocument.mockResolvedValueOnce(new Blob(["pdf"], { type: "application/pdf" }));
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  renderPortal();
  submitRollNumber("2K22-BSCS-210");
  const button = await screen.findByRole("button", { name: "Download Leadership Recognition PDF" });
  fireEvent.click(button);
  await waitFor(() => expect(mocks.downloadDocument).toHaveBeenCalledWith("document-1"));
  await waitFor(() => expect(click).toHaveBeenCalled());
  expect(createObjectURL).toHaveBeenCalled();
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:certificate");
  click.mockRestore();
});
