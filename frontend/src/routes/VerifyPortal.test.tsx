import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test } from "vitest";
import { VerifyPortal } from "./VerifyPortal";

function renderPortal() {
  return render(<MemoryRouter initialEntries={["/verify"]}><Routes><Route path="/verify" element={<VerifyPortal />} /><Route path="/verify/:verificationId" element={<p>Verified route</p>} /></Routes></MemoryRouter>);
}

afterEach(cleanup);

test("keeps malformed verification IDs on the form and explains the canonical format", () => {
  renderPortal();
  fireEvent.change(screen.getByLabelText("Verification ID"), { target: { value: "EMC-ABC" } });
  fireEvent.click(screen.getByRole("button", { name: "Verify document" }));
  expect(screen.getByRole("alert")).toHaveTextContent("EMC-A1B2C3D4");
  expect(screen.queryByText("Verified route")).not.toBeInTheDocument();
});

test("normalizes a well-formed verification ID before opening its record", () => {
  renderPortal();
  fireEvent.change(screen.getByLabelText("Verification ID"), { target: { value: "emc-a2b3c4d5" } });
  fireEvent.click(screen.getByRole("button", { name: "Verify document" }));
  expect(screen.getByText("Verified route")).toBeInTheDocument();
});
