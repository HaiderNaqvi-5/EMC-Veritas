import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { warmReadiness } from "../lib/api/client";
import { AdminPortal } from "./AdminPortal";
import { StudentPortal } from "./StudentPortal";
import { VerifyDocument } from "./VerifyDocument";
import { VerifyPortal } from "./VerifyPortal";

export function App() {
  useEffect(() => {
    warmReadiness();
  }, []);
  return (
    <Routes>
      <Route path="/" element={<StudentPortal />} />
      <Route path="/verify" element={<VerifyPortal />} />
      <Route path="/verify/:verificationId" element={<VerifyDocument />} />
      <Route path="/admin/*" element={<AdminPortal />} />
    </Routes>
  );
}
