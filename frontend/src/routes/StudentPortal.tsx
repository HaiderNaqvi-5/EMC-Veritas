import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { documentDownloadUrl, getStudentDocuments, type PublicDocument } from "../api/documents/public";

function DocumentList({ documents }: { documents: PublicDocument[] }) {
  if (documents.length === 0) return <p>No documents are available in this group yet.</p>;
  return <ul>{documents.map((item) => <li key={item.id}><a href={documentDownloadUrl(item.id)}>{item.title}</a></li>)}</ul>;
}

export function StudentPortal() {
  const [submittedRollNumber, setSubmittedRollNumber] = useState<string | null>(null);
  const [rollNumber, setRollNumber] = useState("");
  const query = useQuery({ queryKey: ["student-documents", submittedRollNumber], queryFn: () => getStudentDocuments(submittedRollNumber!), enabled: !!submittedRollNumber, retry: 2 });
  function submit(event: FormEvent) { event.preventDefault(); if (!query.isFetching && rollNumber.trim()) setSubmittedRollNumber(rollNumber.trim()); }
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
          <button type="submit" disabled={query.isFetching}>Find documents</button>
        </form>
        {query.isFetching && <p role="status">Still loading your records. This may take a moment on the first request.</p>}
        {query.isError && <p role="alert">{query.error.message}</p>}
        {query.data && <section><h2>{query.data.full_name}</h2><h3>Activity Certificates</h3><DocumentList documents={query.data.activity_certificates} /><h3>Leadership & Recognition</h3><DocumentList documents={query.data.leadership_recognition} /></section>}
      </section>
    </main>
  );
}
