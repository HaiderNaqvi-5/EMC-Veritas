import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { verifyDocument } from "../api/documents/public";
import { Skeleton } from "../components/ui/Skeleton";

export function VerifyDocument() {
  const { verificationId = "" } = useParams();
  const query = useQuery({ queryKey: ["verification", verificationId], queryFn: () => verifyDocument(verificationId), retry: 2 });
  if (query.isLoading) return <main><h1>Document verification</h1><p role="status">Checking the authoritative record…</p><div className="mt-6 space-y-3"><Skeleton className="h-6 w-32"/><Skeleton className="h-5 w-64"/><Skeleton className="h-5 w-56"/></div></main>;
  if (query.isError) return <main><h1>Document verification</h1><p role="alert">{query.error.message}</p></main>;
  const record = query.data!;
  return <main><h1>Document verification</h1><p>{record.verified ? "Verified" : record.status}</p><p>{record.full_name} · {record.roll_number}</p><p>{record.document_type}: {record.context}</p><p>Issued: {record.issue_date}</p><p>Verification ID: {record.verification_id}</p></main>;
}
