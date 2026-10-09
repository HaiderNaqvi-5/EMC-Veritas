import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { warmReadiness } from "../lib/api/client";
import { StudentPortal } from "./StudentPortal";

// The public student portal is the busiest route. Keep its initial bundle
// focused on the student flow; admin and verification workspaces load only
// when their routes are visited.
const AdminPortal = lazy(() => import("./AdminPortal").then(({ AdminPortal }) => ({ default: AdminPortal })));
const AdminLogin = lazy(() => import("./AdminLogin").then(({ AdminLogin }) => ({ default: AdminLogin })));
const VerifyDocument = lazy(() => import("./VerifyDocument").then(({ VerifyDocument }) => ({ default: VerifyDocument })));
const VerifyPortal = lazy(() => import("./VerifyPortal").then(({ VerifyPortal }) => ({ default: VerifyPortal })));

export function App() {
  useEffect(() => {
    warmReadiness();
  }, []);
  return (<Suspense fallback={null}>
    <Routes>
      <Route path="/" element={<StudentPortal />} />
      <Route path="/verify" element={<VerifyPortal />} />
      <Route path="/verify/:verificationId" element={<VerifyDocument />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/*" element={<AdminPortal />} />
      <Route path="/student-login" element={<Navigate to="/" replace />} />
      <Route path="/activate" element={<Navigate to="/" replace />} />
    </Routes>
  </Suspense>);
}
