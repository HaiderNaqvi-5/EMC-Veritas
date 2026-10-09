import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { warmReadiness } from "../lib/api/client";
import { StudentPortal } from "./StudentPortal";

// The student portal is the release-burst route.  Keep its initial payload
// limited to the public student journey; these workspaces load only when their
// own URLs are opened, with no change to their rendered UI.
const AdminPortal = lazy(() => import("./AdminPortal").then(({ AdminPortal }) => ({ default: AdminPortal })));
const AdminLogin = lazy(() => import("./AdminLogin").then(({ AdminLogin }) => ({ default: AdminLogin })));
const VerifyDocument = lazy(() => import("./VerifyDocument").then(({ VerifyDocument }) => ({ default: VerifyDocument })));
const VerifyPortal = lazy(() => import("./VerifyPortal").then(({ VerifyPortal }) => ({ default: VerifyPortal })));

export function App() {
  useEffect(() => {
    warmReadiness();
  }, []);
  return (
    <Suspense fallback={null}>
    <Routes>
      <Route path="/" element={<StudentPortal />} />
      <Route path="/verify" element={<VerifyPortal />} />
      <Route path="/verify/:verificationId" element={<VerifyDocument />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/*" element={<AdminPortal />} />
      <Route path="/student-login" element={<Navigate to="/" replace />} />
      <Route path="/activate" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}
