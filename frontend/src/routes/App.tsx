import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { StudentPortal } from "./StudentPortal";
import { VerifyDocument } from "./VerifyDocument";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";

export function App() {
  useEffect(() => { void fetch(`${apiBase}/health/ready`, { credentials: "include" }); }, []);
  return <Routes><Route path="/" element={<StudentPortal />} /><Route path="/verify/:verificationId" element={<VerifyDocument />} /></Routes>;
}
