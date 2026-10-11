import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({ createSupportRequest: vi.fn() }));
vi.mock("../api/support", async () => {
  const actual = await vi.importActual<typeof import("../api/support")>("../api/support");
  return { ...actual, createSupportRequest: mocks.createSupportRequest };
});
import { SupportRequestDialog } from "./SupportRequestDialog";

afterEach(() => { cleanup(); vi.clearAllMocks(); document.body.style.overflow = ""; });

test("submits a student support request and shows its private reference", async () => {
  mocks.createSupportRequest.mockResolvedValueOnce({ ticket_number: "EMC-HELP-A1B2C3D4", status: "OPEN" });
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}><SupportRequestDialog open initialRollNumber="2k22-bscs-238" onClose={() => undefined} /></QueryClientProvider>);

  expect(screen.getByDisplayValue("2K22-BSCS-238")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Student Name" } });
  fireEvent.change(screen.getByLabelText("Email to contact you"), { target: { value: "student@example.com" } });
  fireEvent.change(screen.getByLabelText(/Problem details/), { target: { value: "My activity certificate does not appear." } });
  fireEvent.click(screen.getByRole("button", { name: "Send support request" }));

  await waitFor(() => expect(mocks.createSupportRequest).toHaveBeenCalled());
  expect(mocks.createSupportRequest.mock.calls[0][0]).toEqual(expect.objectContaining({ roll_number: "2K22-BSCS-238", contact_email: "student@example.com" }));
  expect(await screen.findByText("EMC-HELP-A1B2C3D4")).toBeInTheDocument();
});
