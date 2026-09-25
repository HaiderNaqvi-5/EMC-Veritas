import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";

function Arrow() {
  return <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4 fill-none stroke-current stroke-2"><path d="M3 10h13M11 5l5 5-5 5" /></svg>;
}
function CheckIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></svg>;
}
function VerificationSeal() {
  return <div aria-hidden="true" className="verify-seal"><span>EMC</span><strong>V</strong><span>VERIFIED</span></div>;
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
    <main className="verification-v2">
      <header className="verification-v2__header">
        <Link to="/" className="verification-v2__brand">
          <img src="/assets/logos/emc-logo-dark.png" alt="Event Management Club" />
          <span><strong>EMC Veritas</strong><small>EVENT MANAGEMENT CLUB · NFC-IET MULTAN</small></span>
        </Link>
        <Link to="/" className="verification-v2__back">Back to portal <Arrow /></Link>
      </header>

      <section className="verification-v2__hero">
        <div className="verification-v2__grid" aria-hidden="true" />
        <div className="verification-v2__shell">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55 }}>
            <p className="verification-v2__eyebrow">Official document check</p>
            <h1>Verify the <em>record,</em><br />not just the certificate.</h1>
            <p className="verification-v2__lead">Use the verification ID printed on an issued EMC document to confirm its holder, recognition type, issue record, and current status.</p>
            <form onSubmit={submit} className="verification-v2__form">
              <label htmlFor="verification-id">Verification ID</label>
              <div className="verification-v2__lookup">
                <input id="verification-id" value={verificationId} onChange={(event) => setVerificationId(event.target.value)} placeholder="e.g. EMC-ABC123" autoComplete="off" required />
                <Button type="submit">Verify document <Arrow /></Button>
              </div>
              <p>You can find the ID beside the QR code on an issued document.</p>
            </form>
          </motion.div>

          <motion.aside initial={{ opacity: 0, y: 24, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: .7, delay: .12, ease: [0.22, 1, 0.36, 1] }} className="verification-v2__record" aria-label="An example EMC verification record">
            <div className="verification-v2__record-head"><span>EMC VERITAS</span><span>CHECK / 001</span></div>
            <div className="verification-v2__record-body">
              <p className="verification-v2__eyebrow">Verification archive</p>
              <h2>Proof that stays<br />within reach.</h2>
              <div className="verification-v2__checks">
                <div><CheckIcon /><span><strong>Official issue</strong><small>Issued through the EMC workflow</small></span></div>
                <div><CheckIcon /><span><strong>Known holder</strong><small>Matched to the documented recipient</small></span></div>
                <div><CheckIcon /><span><strong>Current status</strong><small>Verified against the live record</small></span></div>
              </div>
            </div>
            <div className="verification-v2__record-foot"><span>Authoritative record</span><VerificationSeal /></div>
          </motion.aside>
        </div>
      </section>

      <footer className="verification-v2__footer">
        <span>Student recognition archive · issued by EMC</span>
        <span className="verification-v2__nfc"><img src="/assets/logos/nfc-iet-logo.png" alt="NFC-IET Multan" />NFC-IET MULTAN</span>
      </footer>
    </main>
  );
}
