import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";

function ScanIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-8 w-8 fill-none stroke-current stroke-[1.5]"
    >
      <path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4M8 8h8v8H8z" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-6 w-6 fill-none stroke-current stroke-[1.8]"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 2.5 2.5L16 9" />
    </svg>
  );
}

export function VerifyPortal() {
  const [verificationId, setVerificationId] = useState("");
  const navigate = useNavigate();
  function submit(event: FormEvent) {
    event.preventDefault();
    const id = verificationId.trim();
    if (id) navigate(`/verify/${encodeURIComponent(id)}`);
  }
  return (
    <main className="verification-page min-h-screen overflow-hidden bg-[#071426] text-white">
      <header className="landing-header">
        <Link to="/" className="flex items-center gap-3">
          <img
            src="/assets/logos/emc-logo.png"
            alt="Event Management Club"
            className="h-11 w-11 object-contain"
          />
          <span>
            <span className="font-serif text-xl">EMC Veritas</span>
            <span className="mt-0.5 block text-[8px] font-semibold tracking-[.16em] text-slate-300">
              OFFICIAL RECOGNITION PORTAL
            </span>
          </span>
        </Link>
        <Link to="/" className="landing-login-link">
          Back to portal
        </Link>
      </header>
      <section className="verification-shell relative mx-auto grid min-h-[calc(100vh-5.25rem)] max-w-6xl items-center gap-12 px-4 py-16 md:grid-cols-[1fr_.9fr]">
        <div className="verification-glow" />
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
        >
          <p className="landing-eyebrow">Independent document check</p>
          <h1 className="landing-hero-title mt-5 text-[clamp(3.1rem,6vw,5.5rem)]">
            Verify with
            <br />
            <em>confidence.</em>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-200">
            Enter a document’s verification ID to confirm that it was issued by
            EMC Veritas and remains valid.
          </p>
          <form onSubmit={submit} className="verification-form mt-8">
            <label
              htmlFor="verification-id"
              className="text-sm font-semibold text-slate-100"
            >
              Verification ID
            </label>
            <div className="landing-lookup mt-2">
              <input
                id="verification-id"
                value={verificationId}
                onChange={(event) => setVerificationId(event.target.value)}
                placeholder="e.g. EMC-ABC123"
                autoComplete="off"
                required
              />
              <Button type="submit">Verify document</Button>
            </div>
          </form>
          <p className="mt-4 text-sm text-slate-400">
            You can find this ID beside the QR code on an issued document.
          </p>
        </motion.div>
        <motion.aside
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.65, delay: 0.12 }}
          className="verification-card"
        >
          <div className="flex items-center justify-between">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[#b7233c] text-white shadow-lg">
              <ScanIcon />
            </div>
            <p className="text-xs font-semibold tracking-[.16em] text-[#e8c172]">
              EMC VERITAS
            </p>
          </div>
          <div className="mt-12 border-y border-white/10 py-7">
            <p className="text-xs font-semibold tracking-[.14em] text-slate-400">
              WHAT A VALID CHECK CONFIRMS
            </p>
            <ul className="mt-5 space-y-4 text-slate-100">
              <li>
                <CheckIcon />
                Issued through the official EMC workflow
              </li>
              <li>
                <CheckIcon />
                The document holder and recognition type
              </li>
              <li>
                <CheckIcon />
                Current validity and issue record
              </li>
            </ul>
          </div>
          <p className="mt-7 font-serif text-2xl leading-tight text-[#f2dec2]">
            A meaningful achievement deserves a trustworthy record.
          </p>
        </motion.aside>
      </section>
    </main>
  );
}
