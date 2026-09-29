import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiRequest } from "../lib/api/client";

type StudentSession = { authenticated: boolean; full_name?: string; roll_number?: string };

export function StudentLogin() {
  const [rollNumber, setRollNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      await apiRequest<StudentSession>("/student-auth/login", { method: "POST", body: JSON.stringify({ roll_number: rollNumber, password }) });
      navigate(`/?roll=${encodeURIComponent(rollNumber)}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to sign in."); }
  }
  return <main className="min-h-screen bg-slate-950 p-6 text-white"><section className="mx-auto mt-20 max-w-md rounded-2xl bg-white p-7 text-slate-900 shadow-xl"><p className="text-xs font-bold tracking-[.16em] text-[#a91f35]">EMC VERITAS</p><h1 className="mt-2 font-serif text-3xl">Student sign in</h1><form className="mt-6 grid gap-4" onSubmit={submit}><input required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} placeholder="Roll number" className="rounded border p-3" /><input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="rounded border p-3" /><button className="rounded bg-[#a91f35] p-3 font-semibold text-white">Sign in</button></form>{error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}<p className="mt-5 text-sm"><Link className="text-[#a91f35] underline" to="/activate">First time here or cannot access your old email?</Link> · <Link className="text-[#a91f35] underline" to="/activate?reset=1">Forgot password?</Link></p></section></main>;
}

export function StudentActivation() {
  const [params] = useSearchParams(); const [rollNumber, setRollNumber] = useState(""); const [fullName, setFullName] = useState(""); const [password, setPassword] = useState(""); const [requestedEmail, setRequestedEmail] = useState(""); const [reason, setReason] = useState(""); const [message, setMessage] = useState(""); const [emailHint, setEmailHint] = useState<string | null>(null); const token = params.get("token"); const recovery = params.get("recover") === "1"; const reset = params.get("reset") === "1" || params.get("mode") === "reset";
  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      if (token) { await apiRequest<void>(reset ? "/student-auth/reset-password" : "/student-auth/activate", { method: "POST", body: JSON.stringify({ token, password }) }); setMessage(reset ? "Your password has been reset. You can now sign in." : "Your account is active. You can now sign in."); }
      else if (recovery) { await apiRequest<void>("/student-auth/recovery-requests", { method: "POST", body: JSON.stringify({ roll_number: rollNumber, requested_email: requestedEmail, reason }) }); setMessage("Your request has been submitted for review. We will use the new email only after approval."); }
      else if (reset) { await apiRequest<void>("/student-auth/request-password-reset", { method: "POST", body: JSON.stringify({ roll_number: rollNumber }) }); setMessage("If your account is eligible, a password-reset email has been sent."); }
      else if (!emailHint) { const result = await apiRequest<{ email_hint: string | null }>("/student-auth/activation-email-hint", { method: "POST", body: JSON.stringify({ roll_number: rollNumber, full_name: fullName }) }); setEmailHint(result.email_hint); setMessage(result.email_hint ? "Does this look like your email? You can now send the activation link." : "We could not confirm a matching roster email. Use recovery if you cannot access it."); }
      else { await apiRequest<void>("/student-auth/request-activation", { method: "POST", body: JSON.stringify({ roll_number: rollNumber }) }); setMessage("If your roster record is eligible, an activation email has been sent."); }
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Unable to complete this request."); }
  }
  return <main className="min-h-screen bg-slate-950 p-6 text-white"><section className="mx-auto mt-20 max-w-md rounded-2xl bg-white p-7 text-slate-900 shadow-xl"><p className="text-xs font-bold tracking-[.16em] text-[#a91f35]">EMC VERITAS</p><h1 className="mt-2 font-serif text-3xl">{token ? reset ? "Choose a new password" : "Set your password" : recovery ? "Update your email" : reset ? "Reset password" : "Activate account"}</h1>{recovery && <p className="mt-3 text-sm text-slate-600">Email changes are approved only after a Super Admin completes your manual, in-person identity verification.</p>}<form className="mt-6 grid gap-4" onSubmit={submit}>{!token && <input required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} placeholder="Roll number" className="rounded border p-3" />}{!token && !recovery && !reset && <input required value={fullName} onChange={(e) => { setFullName(e.target.value); setEmailHint(null); }} placeholder="Full name as it appears on the roster" className="rounded border p-3" />}{emailHint && <p className="rounded border border-amber-300 bg-amber-50 p-3 text-sm">Registered email: <strong>{emailHint}</strong></p>}{recovery && <><input required type="email" value={requestedEmail} onChange={(e) => setRequestedEmail(e.target.value)} placeholder="New email address" className="rounded border p-3" /><textarea required minLength={10} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why can you not access the old email?" className="rounded border p-3" /></>}{token && <input required minLength={12} type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password (12+ characters)" className="rounded border p-3" />}<button className="rounded bg-[#a91f35] p-3 font-semibold text-white">{token ? reset ? "Reset password" : "Activate account" : recovery ? "Submit recovery request" : reset ? "Send password-reset email" : emailHint ? "Send activation email" : "Find my registered email"}</button></form>{message && <p role="status" className="mt-4 text-sm">{message}</p>}<p className="mt-5 text-sm"><Link className="text-[#a91f35] underline" to="/student-login">Back to sign in</Link>{!token && !recovery && !reset && <> · <Link className="text-[#a91f35] underline" to="/activate?recover=1">Cannot access the listed email?</Link></>}</p></section></main>;
}
