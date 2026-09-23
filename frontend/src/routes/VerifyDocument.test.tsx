import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ verifyDocument: vi.fn() }));
vi.mock("../api/documents/public", () => ({ verifyDocument: mocks.verifyDocument }));
import { VerifyDocument } from "./VerifyDocument";

test("verification shows a stable loading state and then authoritative details", async () => {
  mocks.verifyDocument.mockResolvedValueOnce({ verified: true, status: "VALID", verification_id: "EMC-123", full_name: "Ahmed", roll_number: "22-CS-1", document_type: "ACTIVITY_CERTIFICATE", context: "Welcome", activity_date: "2026-01-01", issue_date: "2026-01-02" });
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/verify/EMC-123"]}><Routes><Route path="/verify/:verificationId" element={<VerifyDocument />}/></Routes></MemoryRouter></QueryClientProvider>);
  expect(screen.getByRole("status")).toHaveTextContent("Checking the authoritative record");
  expect(await screen.findByText("Ahmed · 22-CS-1")).toBeInTheDocument();
  expect(mocks.verifyDocument).toHaveBeenCalledWith("EMC-123");
});
