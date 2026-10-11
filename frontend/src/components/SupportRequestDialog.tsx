import { FormEvent, useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  createSupportRequest,
  supportCategoryLabels,
  type SupportCategory,
} from "../api/support";
import { canonicalRollNumber } from "../lib/utils";

type Props = {
  open: boolean;
  initialRollNumber?: string;
  onClose: () => void;
};

const initialForm = {
  roll_number: "",
  full_name: "",
  contact_email: "",
  problem_category: "MISSING_RECORD" as SupportCategory,
  problem_details: "",
  website: "",
};

export function SupportRequestDialog({ open, initialRollNumber = "", onClose }: Props) {
  const firstInput = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState(initialForm);
  const submit = useMutation({ mutationFn: createSupportRequest });

  useEffect(() => {
    if (!open) return;
    setForm((current) => ({
      ...current,
      roll_number: current.roll_number || canonicalRollNumber(initialRollNumber),
    }));
    window.setTimeout(() => firstInput.current?.focus(), 30);
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", escape);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", escape);
    };
  }, [initialRollNumber, onClose, open]);

  if (!open) return null;

  function close() {
    submit.reset();
    onClose();
  }

  function submitForm(event: FormEvent) {
    event.preventDefault();
    if (!submit.isPending) submit.mutate(form);
  }

  return (
    <div className="support-dialog" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) close();
    }}>
      <section role="dialog" aria-modal="true" aria-labelledby="support-dialog-title" className="support-dialog__panel">
        <header className="support-dialog__header">
          <div>
            <p>STUDENT SUPPORT</p>
            <h2 id="support-dialog-title">Tell us what went wrong.</h2>
          </div>
          <button type="button" onClick={close} aria-label="Close support form">×</button>
        </header>

        {submit.data ? (
          <div className="support-dialog__success" role="status">
            <span aria-hidden="true">✓</span>
            <p>Request received</p>
            <h3>{submit.data.ticket_number}</h3>
            <p>Keep this reference number. The EMC team will review your request and contact you at the email address provided.</p>
            <button type="button" onClick={close}>Return to the archive</button>
          </div>
        ) : (
          <form onSubmit={submitForm} className="support-form">
            <p className="support-form__intro">Use this form if a record is missing, incorrect, or will not download. Please provide enough detail for the team to investigate.</p>
            <div className="support-form__grid">
              <label>
                <span>Roll number</span>
                <input ref={firstInput} required minLength={3} maxLength={64} value={form.roll_number} onChange={(event) => setForm({ ...form, roll_number: canonicalRollNumber(event.target.value) })} placeholder="e.g. 2K22-BSCS-238" autoComplete="off" />
              </label>
              <label>
                <span>Full name</span>
                <input required minLength={2} maxLength={255} value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} placeholder="Name on your university record" autoComplete="name" />
              </label>
            </div>
            <div className="support-form__grid">
              <label>
                <span>Email to contact you</span>
                <input required type="email" maxLength={320} value={form.contact_email} onChange={(event) => setForm({ ...form, contact_email: event.target.value })} placeholder="you@example.com" autoComplete="email" />
              </label>
              <label>
                <span>What happened?</span>
                <select value={form.problem_category} onChange={(event) => setForm({ ...form, problem_category: event.target.value as SupportCategory })}>
                  {Object.entries(supportCategoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            </div>
            <label>
              <span>Problem details</span>
              <textarea required minLength={15} maxLength={2000} rows={5} value={form.problem_details} onChange={(event) => setForm({ ...form, problem_details: event.target.value })} placeholder="Describe which activity or certificate is affected, what you expected, and what you see instead." />
              <small>{form.problem_details.length}/2000</small>
            </label>
            <label className="support-form__honeypot" aria-hidden="true">
              Website<input tabIndex={-1} autoComplete="off" value={form.website} onChange={(event) => setForm({ ...form, website: event.target.value })} />
            </label>
            {submit.isError && <p className="support-form__error" role="alert">{submit.error.message}</p>}
            <div className="support-form__actions">
              <p>Your information is visible only to authorized EMC administrators.</p>
              <button type="submit" disabled={submit.isPending}>{submit.isPending ? "Sending request…" : "Send support request"}<span aria-hidden="true">→</span></button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
