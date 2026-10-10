import { lazy, Suspense, useEffect } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { warmReadiness } from "../lib/api/client";
import { StudentPortal } from "./StudentPortal";
import { usePublicTheme } from "../lib/publicTheme";
import { PublicThemeToggle } from "../components/PublicThemeToggle";

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
    <Routes>
      <Route path="/" element={<StudentPortal />} />
      <Route path="/verify" element={<Suspense fallback={<PublicRouteFallback />}><VerifyPortal /></Suspense>} />
      <Route path="/verify/:verificationId" element={<Suspense fallback={<PublicRouteFallback />}><VerifyDocument /></Suspense>} />
      <Route path="/admin/login" element={<Suspense fallback={null}><AdminLogin /></Suspense>} />
      <Route path="/admin/*" element={<Suspense fallback={null}><AdminPortal /></Suspense>} />
      <Route path="/student-login" element={<Navigate to="/" replace />} />
      <Route path="/activate" element={<Navigate to="/" replace />} />
      <Route path="*" element={<PublicNotFound />} />
    </Routes>
  );
}

function PublicNotFound() {
  const { theme, toggleTheme } = usePublicTheme();
  return <main className={`public-not-found public-not-found--${theme}`}>
    <header className="public-not-found__header">
      <Link to="/" className="public-not-found__brand">
        <img src={theme === "dark" ? "/assets/logos/emc-logo-dark.png" : "/assets/logos/emc-logo.png"} alt="Event Management Club" />
        <span>EMC Veritas</span>
      </Link>
      <PublicThemeToggle theme={theme} onToggle={toggleTheme} compact />
    </header>
    <section className="public-not-found__content" aria-labelledby="not-found-title">
      <p>404 · Record route not found</p>
      <h1 id="not-found-title">This page is not part of the archive.</h1>
      <p>The address may be incomplete or outdated. Return to the public portal, or open the verification screen and enter the ID printed beside the QR code.</p>
      <div>
        <Link to="/">Return to portal <span aria-hidden="true">→</span></Link>
        <Link to="/verify">Verify a record <span aria-hidden="true">→</span></Link>
      </div>
    </section>
  </main>;
}

function PublicRouteFallback() {
  const { theme } = usePublicTheme();
  return <main className={`public-route-loading public-route-loading--${theme}`} role="status" aria-label="Loading EMC Veritas">
    <div className="public-route-loading__brand"><img src={theme === "dark" ? "/assets/logos/emc-logo-dark.png" : "/assets/logos/emc-logo.png"} alt="" /><span>EMC Veritas</span></div>
    <div className="public-route-loading__line" />
    <p>Opening the verification archive…</p>
  </main>;
}
