import { useParams } from "react-router-dom";
export function VerifyDocument() { const { verificationId } = useParams(); return <main><h1>Document verification</h1><p>Verification ID: {verificationId}</p></main>; }
