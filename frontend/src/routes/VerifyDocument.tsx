import { type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { verifyDocument } from "../api/documents/public";
import { Skeleton } from "../components/ui/Skeleton";

function CheckIcon() { return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-7 w-7 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></svg>; }
function Arrow() { return <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4 fill-none stroke-current stroke-2"><path d="M3 10h13M11 5l5 5-5 5" /></svg>; }

export function VerifyDocument() {
  const { verificationId = "" } = useParams();
  const query = useQuery({ queryKey: ["verification", verificationId], queryFn: () => verifyDocument(verificationId), retry: 2 });

  if (query.isLoading) return <VerificationLayout><p role="status" className="verification-result__eyebrow">Checking the authoritative record…</p><div className="mt-7 space-y-3"><Skeleton className="h-7 w-44" /><Skeleton className="h-5 w-full" /><Skeleton className="h-5 w-4/5" /></div></VerificationLayout>;
  if (query.isError) return <VerificationLayout><p role="alert" className="verification-result__error">{query.error.message}</p><Link to="/verify" className="verification-result__link">Try another verification ID <Arrow /></Link></VerificationLayout>;

  const record = query.data!;
  return <VerificationLayout>
    <div className="verification-result__status"><div><CheckIcon /></div><span><p className="verification-result__eyebrow">Authoritative result</p><h1>{record.verified ? "Document verified" : record.status}</h1></span></div>
    <p className="verification-result__summary">This record has been checked against EMC Veritas’ issued-document archive.</p>
    <dl className="verification-result__details">
      <Detail label="Document holder" value={`${record.full_name} · ${record.roll_number}`} />
      <Detail label="Document type" value={record.document_type.split("_").join(" ")} />
      <Detail label="Recognition context" value={record.context} />
      <Detail label="Issued" value={record.issue_date} />
      <Detail label="Verification ID" value={record.verification_id} />
    </dl>
    <Link to="/verify" className="verification-result__link">Verify another document <Arrow /></Link>
  </VerificationLayout>;
}

function Detail({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
function VerificationLayout({ children }: { children: ReactNode }) {
  return <main className="verification-v2 verification-v2--result">
    <header className="verification-v2__header">
      <Link to="/" className="verification-v2__brand"><img src="/assets/logos/emc-logo-dark.png" alt="Event Management Club" /><span><strong>EMC Veritas</strong><small>EVENT MANAGEMENT CLUB · NFC-IET MULTAN</small></span></Link>
      <Link to="/verify" className="verification-v2__back">Verify another <Arrow /></Link>
    </header>
    <section className="verification-result"><div className="verification-result__card">{children}</div></section>
  </main>;
}
