import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { documentDownloadUrl, getStudentDocuments, type PublicDocument } from "../api/documents/public";
import { AdminLoginModal } from "../features/auth/AdminLoginModal";
import { authApi } from "../features/auth/contracts";

function DocumentList({ documents }: { documents: PublicDocument[] }) {
  if (documents.length === 0) return <p>No documents are available in this group yet.</p>;
  return <ul>{documents.map((item) => <li key={item.id}><a href={documentDownloadUrl(item.id)}>{item.title}</a></li>)}</ul>;
}

export function StudentPortal() {
  const [submittedRollNumber, setSubmittedRollNumber] = useState<string | null>(null);
  const [rollNumber, setRollNumber] = useState("");
  const [adminRollNumber, setAdminRollNumber] = useState<string | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [checkingLookup, setCheckingLookup] = useState(false);
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["student-documents", submittedRollNumber], queryFn: () => getStudentDocuments(submittedRollNumber!), enabled: !!submittedRollNumber, retry: 2 });
  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = rollNumber.trim();
    if (!normalized || query.isFetching || checkingLookup) return;
    setLookupError(null);
    setCheckingLookup(true);
    try {
      const lookup = await authApi.lookup(normalized);
      if (lookup.is_admin && lookup.active) setAdminRollNumber(normalized);
      else setSubmittedRollNumber(normalized);
    } catch (error) {
      setLookupError(error instanceof Error ? error.message : "Unable to check this roll number.");
    } finally {
      setCheckingLookup(false);
    }
  }
  async function login(password: string) {
    if (!adminRollNumber) return;
    const session = await authApi.login(adminRollNumber, password);
    if (!session.authenticated) throw new Error("Unable to sign in.");
    navigate("/admin");
  }
  return (
    <main className="student-portal">
      <header className="brand-bar" aria-label="Institutional branding">
        <img src="/assets/logos/nfc-iet-logo.png" alt="NFC-IET Multan" />
        <img src="/assets/logos/emc-logo.png" alt="Event Management Club" />
      </header>
      <section className="lookup-card">
        <p className="eyebrow">Event Management Club · NFC-IET Multan</p>
        <h1>EMC Veritas</h1>
        <p>Enter your roll number to find available certificates and recognition letters.</p>
        <form onSubmit={submit}>
          <label htmlFor="roll-number">Roll number</label>
          <input id="roll-number" name="roll-number" value={rollNumber} onChange={(event) => setRollNumber(event.target.value)} autoComplete="off" required />
          <button type="submit" disabled={query.isFetching || checkingLookup}>{checkingLookup ? "Checking…" : "Find documents"}</button>
        </form>
        {lookupError && <p role="alert">{lookupError}</p>}
        {query.isFetching && <p role="status">Still loading your records. This may take a moment on the first request.</p>}
        {query.isError && <p role="alert">{query.error.message}</p>}
        {query.data && <section><h2>{query.data.full_name}</h2><h3>Activity Certificates</h3><DocumentList documents={query.data.activity_certificates} /><h3>Leadership & Recognition</h3><DocumentList documents={query.data.leadership_recognition} /></section>}
      </section>
      {adminRollNumber && <AdminLoginModal rollNumber={adminRollNumber} onSubmit={login} onClose={() => setAdminRollNumber(null)} />}
    </main>
  );
}
