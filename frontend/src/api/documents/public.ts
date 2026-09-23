export type PublicDocument = { id: string; title: string; issue_date: string; status: string };
export type StudentDocuments = { full_name: string; roll_number: string; activity_certificates: PublicDocument[]; leadership_recognition: PublicDocument[] };
const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";
export async function getStudentDocuments(rollNumber: string): Promise<StudentDocuments> {
  const response = await fetch(`${apiBase}/public/students/${encodeURIComponent(rollNumber)}/documents`);
  if (!response.ok) throw new Error(response.status === 404 ? "No certificates or letters are currently available for this roll number." : "Unable to load records right now.");
  return response.json();
}
