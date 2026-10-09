import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ apiRequest: vi.fn() }));
vi.mock("../../lib/api/client", () => ({ apiRequest: mocks.apiRequest }));
import { DocumentsPage } from "./DocumentsPage";

const activity = { id: "activity-1", name: "Farewell", activity_date: "2026-10-09", status: "PUBLISHED" };
const documents = [
  { id: "ec-1", student_id: "student-1", student_name: "One", roll_number: "R-1", activity_id: activity.id, document_type: "EXECUTIVE_COUNCIL_CERTIFICATE", verification_id: "EMC-11111111", issue_date: "2026-10-09", status: "VALID", version: 1, storage_key: "issued/ec-1.pdf" },
  { id: "ec-2", student_id: "student-2", student_name: "Two", roll_number: "R-2", activity_id: activity.id, document_type: "EXECUTIVE_COUNCIL_CERTIFICATE", verification_id: "EMC-22222222", issue_date: "2026-10-09", status: "VALID", version: 1, storage_key: null },
];

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <DocumentsPage />
    </QueryClientProvider>,
  );
}

afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("shows EC readiness and prepares EC PDFs through the dedicated batch endpoint", async () => {
  mocks.apiRequest.mockImplementation((path: string) => {
    if (path === "/admin/documents") return Promise.resolve(documents);
    if (path === "/admin/activities") return Promise.resolve([activity]);
    if (path.includes("pre-generate-ec")) return Promise.resolve({ total_documents: 2, ready_documents: 2, generated_documents: 1, remaining_documents: 0, failed_document_ids: [] });
    return Promise.resolve({});
  });
  renderPage();

  const select = await screen.findByLabelText("Executive Council certificate activity");
  expect(await screen.findByRole("option", { name: /Farewell.*1\/2 ready/ })).toBeInTheDocument();
  fireEvent.change(select, { target: { value: activity.id } });
  fireEvent.click(screen.getByRole("button", { name: "Prepare next 5 EC PDFs" }));

  await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalledWith(
    "/admin/documents/activities/activity-1/pre-generate-ec?limit=5",
    { method: "POST" },
  ));
  expect(await screen.findByText(/Ready: 2\/2.*Remaining: 0/)).toBeInTheDocument();
});
