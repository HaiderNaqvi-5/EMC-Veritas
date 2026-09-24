import { type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { verifyDocument } from "../api/documents/public";
import { Skeleton } from "../components/ui/Skeleton";

function CheckIcon() { return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-9 w-9 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></svg>; }

export function VerifyDocument() {
  const { verificationId = "" } = useParams(); const query = useQuery({ queryKey: ["verification", verificationId], queryFn: () => verifyDocument(verificationId), retry: 2 });
  if (query.isLoading) return <VerificationLayout><p role="status" className="text-slate-300">Checking the authoritative record…</p><div className="mt-6 space-y-3"><Skeleton className="h-6 w-32"/><Skeleton className="h-5 w-64"/><Skeleton className="h-5 w-56"/></div></VerificationLayout>;
  if (query.isError) return <VerificationLayout><p role="alert" className="rounded-xl border border-red-300/20 bg-red-950/40 p-4 text-red-100">{query.error.message}</p><Link to="/verify" className="mt-5 inline-block text-sm font-semibold text-[#e8c172]">Try another verification ID</Link></VerificationLayout>;
  const record = query.data!;
  return <VerificationLayout><div className="flex items-center gap-4"><div className="grid h-16 w-16 place-items-center rounded-full bg-emerald-400 text-[#082036]"><CheckIcon /></div><div><p className="landing-eyebrow">Authoritative result</p><h1 className="mt-1 font-serif text-4xl">{record.verified ? "Document verified" : record.status}</h1></div></div><div className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2"><Detail label="Document holder" value={`${record.full_name} · ${record.roll_number}`} /><Detail label="Document type" value={record.document_type.split("_").join(" ")} /><Detail label="Recognition context" value={record.context} /><Detail label="Issued" value={record.issue_date} /><Detail label="Verification ID" value={record.verification_id} /></div><Link to="/verify" className="mt-7 inline-block text-sm font-semibold text-[#e8c172]">Verify another document</Link></VerificationLayout>;
}
function Detail({ label, value }: { label: string; value: string }) { return <div className="bg-[#0b233d] p-5"><p className="text-xs font-semibold tracking-[.14em] text-slate-400">{label}</p><p className="mt-2 text-sm font-medium text-white">{value}</p></div>; }
function VerificationLayout({ children }: { children: ReactNode }) { return <main className="verification-page min-h-screen bg-[#071426] text-white"><header className="landing-header"><Link to="/" className="flex items-center gap-3"><img src="/assets/logos/emc-logo.png" alt="Event Management Club" className="h-11 w-11 object-contain" /><span className="font-serif text-xl">EMC Veritas</span></Link><Link to="/verify" className="landing-login-link">Verify a document</Link></header><section className="mx-auto max-w-3xl px-4 py-20"><div className="rounded-3xl border border-white/10 bg-[#102a48] p-7 shadow-2xl md:p-10">{children}</div></section></main>; }
