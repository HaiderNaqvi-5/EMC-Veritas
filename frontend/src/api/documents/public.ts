export type PublicDocument = { id: string; title: string; issue_date: string; status: string };
export type StudentDocuments = { full_name: string; roll_number: string; activity_certificates: PublicDocument[]; leadership_recognition: PublicDocument[] };
const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";
export async function getStudentDocuments(rollNumber: string): Promise<StudentDocuments> {
  const response = await fetch(`${apiBase}/public/students/${encodeURIComponent(rollNumber)}/documents`);
  if (!response.ok) throw new Error(response.status === 404 ? "No certificates or letters are currently available for this roll number." : "Unable to load records right now.");
  return response.json();
}

export function documentDownloadUrl(documentId: string): string {
  return `${apiBase}/public/documents/${encodeURIComponent(documentId)}/download`;
}
export type Verification = { verified: boolean; status: string; verification_id: string; full_name: string; roll_number: string; document_type: string; context: string; activity_date: string | null; issue_date: string };
export class VerificationError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "VerificationError";
    this.status = status;
  }
}
export async function verifyDocument(verificationId: string): Promise<Verification> {
  const response = await fetch(`${apiBase}/public/verify/${encodeURIComponent(verificationId)}`);
  if (!response.ok) throw new VerificationError(
    response.status,
    response.status === 404
      ? "No record matches this verification ID."
      : "Verification is temporarily unavailable. Please try again in a moment.",
  );
  return response.json();
}
