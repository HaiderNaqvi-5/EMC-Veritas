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

test("shows progress while downloading an issued leadership document", async () => {
  mocks.getStudentDocuments.mockResolvedValueOnce({
    full_name: "Student",
    activity_certificates: [],
    leadership_recognition: [{ id: "document-1", title: "Leadership Recognition", issue_date: "2026-10-08", status: "VALID", download_url: "https://storage.test/signed" }],
  });
  let finishDownload: ((value: Blob) => void) | undefined;
  mocks.downloadDocument.mockReturnValueOnce(new Promise<Blob>((resolve) => { finishDownload = resolve; }));
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:pdf") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  renderPortal();
  submitRollNumber("2K22-BSCS-210");
  const button = await screen.findByRole("button", { name: "Download Leadership Recognition PDF" });
  fireEvent.click(button);
  expect(await screen.findByText("Downloading your PDF now. Keep this page open for a moment.")).toBeInTheDocument();
  await waitFor(() => expect(mocks.downloadDocument).toHaveBeenCalledWith(expect.objectContaining({ id: "document-1" })));
  finishDownload?.(new Blob(["pdf"], { type: "application/pdf" }));
  expect(await screen.findByText("Download started. Check your browser’s downloads.")).toBeInTheDocument();
  expect(screen.getByText("Issued 8 Oct 2026 · Official PDF")).toBeInTheDocument();
  click.mockRestore();
});
