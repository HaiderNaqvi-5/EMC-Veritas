import { FormEvent, type ReactNode, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  documentDownloadUrl,
  getStudentDocuments,
  type PublicDocument,
} from "../api/documents/public";
import { AdminLoginModal } from "../features/auth/AdminLoginModal";
import { authApi } from "../features/auth/contracts";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { canonicalRollNumber } from "../lib/utils";

function Arrow() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className="h-4 w-4 fill-none stroke-current stroke-2"
    >
      <path d="M3 10h13M11 5l5 5-5 5" />
    </svg>
  );
}
function Shield() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-6 w-6 fill-none stroke-current stroke-[1.7]"
    >
      <path d="M12 3 4.5 6v5.4c0 4.6 3 7.8 7.5 9.6 4.5-1.8 7.5-5 7.5-9.6V6L12 3Z" />
      <path d="m8.5 12 2.2 2.2 4.8-5" />
    </svg>
  );
}
function FileIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-6 w-6 fill-none stroke-current stroke-[1.7]"
    >
      <path d="M6 3h8l4 4v14H6z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </svg>
  );
}
function Spark() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-6 w-6 fill-none stroke-current stroke-[1.7]"
    >
      <path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" />
    </svg>
  );
}
function VerificationMark() {
  return (
    <div className="verification-mark" aria-hidden="true">
      <div className="verification-mark__halo" />
      <div className="verification-mark__core"><Shield /></div>
      <span>EMC<br />VERIFIED</span>
    </div>
  );
}

function VeritasSeal({ small = false }: { small?: boolean }) {
  return (
    <div
      aria-label="EMC Veritas seal"
      className={`grid place-items-center rounded-full border border-[#f1c576]/60 bg-[#a91f35] text-center text-[#ffe6b0] shadow-[0_0_0_5px_rgba(169,31,53,.2)] ${small ? "h-12 w-12" : "h-20 w-20"}`}
    >
      <div
        className={`rounded-full border border-[#ffe6b0]/60 ${small ? "h-9 w-9 pt-1" : "h-16 w-16 pt-2"}`}
      >
        <p
          className={`${small ? "text-[5px]" : "text-[7px]"} tracking-[.16em]`}
        >
          EMC
        </p>
        <p
          className={`${small ? "mt-0.5 text-[10px]" : "mt-1 text-xl"} font-serif leading-none`}
        >
          V
        </p>
        <p
          className={`${small ? "text-[4px]" : "text-[6px]"} tracking-[.14em]`}
        >
          VERITAS
        </p>
      </div>
    </div>
  );
}
function CertificatePreview() {
  return (
    <motion.div
      initial={{ opacity: 0, rotate: 4, y: 24 }}
      animate={{ opacity: 1, rotate: 2, y: 0 }}
      transition={{ duration: 0.8, delay: 0.18 }}
      className="certificate-preview relative mx-auto max-w-[30rem] rounded-[.35rem] p-3 shadow-2xl"
    >
      <div className="certificate-inner relative min-h-[25rem] overflow-hidden rounded-[.15rem] px-7 py-8 text-center text-slate-900 sm:px-10">
        <div className="absolute left-3 top-3 h-14 w-14 border-l-4 border-t-4 border-[#a91f35]" />
        <div className="absolute right-3 top-3 h-14 w-14 border-r-4 border-t-4 border-[#a91f35]" />
        <div className="absolute bottom-3 left-3 h-14 w-14 border-b-4 border-l-4 border-[#a91f35]" />
        <div className="absolute bottom-3 right-3 h-14 w-14 border-b-4 border-r-4 border-[#a91f35]" />
        <div className="mx-auto flex max-w-[13rem] items-center justify-center gap-2 border-b border-[#bd263e]/30 pb-3">
          <VeritasSeal small />
          <div className="text-left">
            <p className="font-serif text-lg leading-none">EMC Veritas</p>
            <p className="mt-1 text-[7px] font-semibold tracking-[.15em]">
              NFC-IET MULTAN
            </p>
          </div>
        </div>
        <p className="mt-8 text-[10px] font-semibold tracking-[.24em] text-[#a91f35]">
          OFFICIAL RECOGNITION
        </p>
        <h2 className="mt-3 font-serif text-3xl">
          Certificate of Participation
        </h2>
        <p className="mt-5 text-xs">This is to certify that</p>
        <p className="mt-2 font-serif text-2xl italic">Your Name Here</p>
        <div className="mx-auto mt-2 w-44 border-t border-slate-400" />
        <p className="mx-auto mt-5 max-w-xs text-[11px] leading-relaxed text-slate-600">
          has actively participated in an EMC event and contributed to its
          successful execution.
        </p>
        <div className="absolute bottom-7 left-8 text-left">
          <div className="h-px w-20 bg-slate-500" />
          <p className="mt-1 text-[7px]">Faculty Advisor</p>
        </div>
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2">
          <VeritasSeal small />
        </div>
        <div className="absolute bottom-7 right-8 text-right">
          <div className="h-px w-20 bg-slate-500" />
          <p className="mt-1 text-[7px]">President, EMC</p>
        </div>
      </div>
    </motion.div>
  );
}
function RecognitionCanvas() {
  return (
    <motion.aside className="portal-preview" initial={{ opacity: 0, y: 28, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: .8, delay: .12, ease: [0.22, 1, 0.36, 1] }} aria-label="EMC Veritas portal preview">
      <div className="portal-preview__rail"><strong>EMC<br />VERITAS</strong><span className="portal-preview__rail-dot" /><span>ARCHIVE</span><span>VERIFY</span><span>RECORDS</span></div>
      <div className="portal-preview__main">
        <div className="portal-preview__header"><span>RECOGNITION RECORD</span><span className="portal-preview__status"><Shield /> VERIFIED SYSTEM</span></div>
        <div className="portal-preview__identity"><div className="portal-preview__avatar">EV</div><div><p>EMC Veritas archive</p><strong>Your issued records, in one place.</strong><span>Search by roll number to begin</span></div></div>
        <div className="portal-preview__tabs"><span className="is-active">Overview</span><span>Records</span><span>Verification</span></div>
        <div className="portal-preview__content"><div className="portal-preview__timeline"><p>WHAT A RECORD CAN INCLUDE</p><div><i /><span><strong>Participation</strong><small>Official event involvement</small></span></div><div><i /><span><strong>Appreciation</strong><small>Recognised contribution</small></span></div><div><i /><span><strong>Leadership</strong><small>Role and responsibility</small></span></div></div><div className="portal-preview__certificate"><p>ISSUED BY EMC</p><FileIcon /><strong>A record designed<br />to be useful.</strong><span>Downloadable · Verifiable</span><VeritasSeal small /></div></div>
      </div>
    </motion.aside>
  );
}
function DocumentList({ documents }: { documents: PublicDocument[] }) {
  if (documents.length === 0)
    return (
      <p className="mt-3 text-sm text-slate-600">
        No documents are available in this group yet.
      </p>
    );
  return (
    <ul className="mt-3 grid gap-2">
      {documents.map((item) => (
        <li key={item.id}>
          <a
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#a91f35] underline decoration-[#a91f35]/30 underline-offset-4 hover:text-[#7f1228]"
            href={documentDownloadUrl(item.id)}
          >
            <FileIcon />
            {item.title}
          </a>
        </li>
      ))}
    </ul>
  );
}
function ResultSkeleton() {
  return (
    <section aria-label="Loading student records" className="mt-6 space-y-4">
      <Skeleton className="h-7 w-48" />
      <Skeleton className="h-4 w-36" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-4 w-44" />
      <Skeleton className="h-20 w-full" />
    </section>
  );
}
const archiveChapters = [
  {
    number: "01",
    kicker: "The moment",
    title: "An EMC activity becomes a record.",
    copy: "The archive starts with the work itself: an event, a contribution, and the role you played in making it happen.",
    type: "Participation",
    detail: "Event involvement",
  },
  {
    number: "02",
    kicker: "The recognition",
    title: "Issued when it is official.",
    copy: "Recognition is recorded by EMC only when it has been issued—not as a claim, a badge, or a social post.",
    type: "Appreciation",
    detail: "Recognised contribution",
  },
  {
    number: "03",
    kicker: "The proof",
    title: "Useful beyond the event itself.",
    copy: "A record remains easy to find, download, and verify when someone needs to confirm what you did.",
    type: "Leadership",
    detail: "Verifiable role record",
  },
];
function ArchiveStory() {
  const [active, setActive] = useState(0);
  const current = archiveChapters[active];
  return (
    <section id="document-types" className="archive-story">
      <div className="landing-shell archive-story__grid">
        <div className="archive-story__sticky">
          <p className="landing-eyebrow">The archive, in motion</p>
          <p className="archive-story__count">0{active + 1}<span> / 03</span></p>
          <h2 aria-live="polite">{current.title}</h2>
          <p>{current.copy}</p>
          <div className="archive-story__progress" aria-hidden="true">
            {archiveChapters.map((chapter, index) => <i key={chapter.number} className={index <= active ? "is-active" : ""} />)}
          </div>
        </div>
        <div className="archive-story__chapters">
          {archiveChapters.map((chapter, index) => (
            <motion.article
              key={chapter.number}
              className={`archive-story__chapter ${index === active ? "is-active" : ""}`}
              initial={{ opacity: 0, y: 38 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.6 }}
              onViewportEnter={() => setActive(index)}
              transition={{ duration: .7, ease: [0.22, 1, 0.36, 1] }}
            >
              <span>{chapter.number}</span>
              <p>{chapter.kicker}</p>
              <h3>{chapter.title}</h3>
              <div className="archive-story__record"><div><small>RECORD TYPE</small><strong>{chapter.type}</strong><em>{chapter.detail}</em></div><VerificationMark /></div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
export function StudentPortal() {
  const [theme, setTheme] = useState<"dark" | "light">("light");
  const [submittedRollNumber, setSubmittedRollNumber] = useState<string | null>(
    null,
  );
  const [rollNumber, setRollNumber] = useState("");
  const [adminRollNumber, setAdminRollNumber] = useState<string | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [checkingLookup, setCheckingLookup] = useState(false);
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ["student-documents", submittedRollNumber],
    queryFn: () => getStudentDocuments(submittedRollNumber!),
    enabled: !!submittedRollNumber,
    retry: 2,
  });
  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = rollNumber.trim();
    if (!normalized || query.isFetching || checkingLookup) return;
    setLookupError(null);
    setCheckingLookup(true);
    try {
      const lookup = await authApi.lookup(normalized);
      if (lookup.is_admin && lookup.active) setAdminRollNumber(normalized);
      else setSubmittedRollNumber(normalized);
    } catch (error) {
      setLookupError(
        error instanceof Error
          ? error.message
          : "Unable to check this roll number.",
      );
    } finally {
      setCheckingLookup(false);
    }
  }
  async function login(password: string) {
    if (!adminRollNumber) return;
    const session = await authApi.login(adminRollNumber, password);
    if (!session.authenticated) throw new Error("Unable to sign in.");
    navigate("/admin");
  }
  const scrollToLookup = () =>
    document
      .getElementById("document-lookup")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  return (
    <main className={`landing-page landing-page--${theme} overflow-hidden`}>
      <header className="landing-header">
        <a href="#top" className="flex items-center gap-3">
          <img
            src={theme === "dark" ? "/assets/logos/emc-logo-dark.png" : "/assets/logos/emc-logo.png"}
            alt="Event Management Club"
            className="h-11 w-11 object-contain"
          />
          <span>
            <span className="font-serif text-xl">EMC Veritas</span>
            <span className="mt-0.5 block text-[10px] font-semibold tracking-[.12em] text-slate-300">
              EVENT MANAGEMENT CLUB · NFC-IET MULTAN
            </span>
          </span>
        </a>
        <nav
          aria-label="Primary navigation"
          className="hidden items-center gap-7 text-sm text-slate-200 lg:flex"
        >
          <a href="#how-it-works">How it works</a>
          <a href="#document-types">Document types</a>
          <Link to="/verify">Verify</Link>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
            className="landing-theme-toggle"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          >
            <span aria-hidden="true">{theme === "dark" ? "☼" : "◐"}</span>
            <span className="hidden sm:inline">{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
          <Link to="/verify" className="landing-login-link">
            Verify a record <Arrow />
          </Link>
        </div>
      </header>
      <section id="top" className="landing-hero relative">
        <div className="landing-hero-grid" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_27%,rgba(152,30,50,.28),transparent_31%),radial-gradient(circle_at_8%_38%,rgba(202,155,72,.1),transparent_25%)]" />
        <div className="landing-shell relative grid items-center gap-12 py-16 lg:grid-cols-[.95fr_1.05fr] lg:py-24">
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.65 }}
          >
            <p className="landing-eyebrow">Event Management Club · NFC-IET Multan</p>
            <h1 className="landing-hero-title mt-5">
              Your work deserves
              <br />
              <em>a record.</em>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-200">
              A permanent, verifiable archive for the contributions you make
              through EMC.
            </p>
            <form
              id="document-lookup"
              onSubmit={submit}
              className="landing-lookup mt-8"
            >
              <label className="sr-only" htmlFor="roll-number">
                Roll number
              </label>
              <input
                id="roll-number"
                name="roll-number"
                value={rollNumber}
                onChange={(event) => setRollNumber(canonicalRollNumber(event.target.value))}
                placeholder="e.g. 2k22-BSCS-238"
                autoComplete="off"
                required
              />
              <Button
                type="submit"
                disabled={query.isFetching || checkingLookup}
              >
                {checkingLookup ? "Checking…" : "Find my record"}
                <Arrow />
              </Button>
            </form>
            <div className="hero-principles mt-7"><span>Find</span><span>Keep</span><span>Verify</span></div>
            {lookupError && (
              <p
                role="alert"
                className="mt-5 rounded-lg border border-red-300/30 bg-red-950/50 p-3 text-sm text-red-100"
              >
                {lookupError}
              </p>
            )}
            {query.isFetching && (
              <>
                <p role="status" className="mt-5 text-sm text-slate-200">
                  Still loading your records. This may take a moment on the
                  first request.
                </p>
                <ResultSkeleton />
              </>
            )}
            {query.isError && (
              <p
                role="alert"
                className="mt-5 rounded-lg border border-red-300/30 bg-red-950/50 p-3 text-sm text-red-100"
              >
                {query.error.message}
              </p>
            )}
            {query.data && (
              <section className="mt-6 rounded-2xl border border-white/15 bg-white/95 p-5 text-slate-900 shadow-2xl">
                <p className="text-xs font-bold tracking-[.15em] text-[#a91f35]">
                  YOUR DOCUMENTS
                </p>
                <h2 className="mt-1 font-serif text-2xl">
                  {query.data.full_name}
                </h2>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <h3 className="font-semibold">Activity certificates</h3>
                    <DocumentList
                      documents={query.data.activity_certificates}
                    />
                  </div>
                  <div>
                    <h3 className="font-semibold">Leadership & recognition</h3>
                    <DocumentList
                      documents={query.data.leadership_recognition}
                    />
                  </div>
                </div>
              </section>
            )}
          </motion.div>
          <RecognitionCanvas />
        </div>
      </section>
      <ArchiveStory />
      <section id="how-it-works" className="landing-shell journey-section py-28">
        <div className="journey-section__intro">
          <div>
            <p className="landing-eyebrow">From activity to proof</p>
            <h2 className="landing-title mt-3">A record, ready when it matters.</h2>
          </div>
          <p>Veritas turns an EMC contribution into something you can retrieve, share, and verify without chasing old messages or folders.</p>
        </div>
        <div className="record-flow mt-16">
          {[
            [
              "01",
              "Locate your record",
              "Use the roll number NFC-IET already knows you by. There is no new account to create.",
              "YOUR ROLL NUMBER",
              <FileIcon />,
            ],
            [
              "02",
              "Review what is issued",
              "See participation, appreciation, and leadership records that EMC has officially issued to you.",
              "YOUR ISSUED RECORDS",
              <Spark />,
            ],
            [
              "03",
              "Use it with confidence",
              "Download a record when required, or use its verification route when someone needs to confirm it.",
              "DOWNLOAD OR VERIFY",
              <Shield />,
            ],
          ].map(([number, title, copy, label, icon]) => (
            <motion.div
              key={String(number)}
              className="record-flow__item"
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.05 }}
              transition={{ duration: 0.42, delay: Number(number) * 0.06 }}
            >
              <div className="record-flow__marker"><span>{number}</span><i /></div>
              <div className="record-flow__copy"><p className="landing-eyebrow">{label}</p><h3>{title}</h3><p>{copy}</p></div>
              <div className="record-flow__icon">{icon as ReactNode}</div>
            </motion.div>
          ))}
        </div>
      </section>
      <section id="verify" className="landing-shell verification-section pb-28">
        <Link
          to="/verify"
          className="landing-verify grid items-center gap-8 rounded-3xl border border-[#e7c577]/20 p-7 md:grid-cols-[auto_1fr] md:p-10"
        >
          <VerificationMark />
          <div>
            <p className="landing-eyebrow">Document verification</p>
            <h2 className="landing-title mt-3 text-4xl">
              Check the record, not just the certificate.
            </h2>
            <p className="landing-verify-copy mt-4 max-w-2xl leading-7 text-slate-300">
              Use the document’s verification route whenever a faculty member,
              employer, or society needs confirmation of an issued record.
            </p>
            <span className="verification-section__proof">The verification screen confirms holder, record type, issue date, and current status</span>
            <span className="landing-verify-action mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#e8c172]">Open verification <Arrow /></span>
          </div>
        </Link>
      </section>
      <section className="landing-closing" aria-labelledby="archive-closing-title">
        <div className="landing-shell landing-closing__inner">
          <div>
            <p className="landing-eyebrow">Keep the work within reach</p>
            <h2 id="archive-closing-title" className="landing-closing__quote">Your contribution deserves <em>a place you can return to.</em></h2>
            <p className="landing-closing__copy">Search when you need your record. Verify it when someone else needs confidence in it.</p>
            <button type="button" onClick={scrollToLookup} className="landing-closing__action">Find my record <Arrow /></button>
          </div>
          <div className="landing-closing__note"><span>EMC VERITAS</span><strong>Student recognition<br />archive</strong><p>Issued records. Clear proof.</p></div>
        </div>
      </section>
      <footer className="border-t border-white/10">
        <div className="landing-shell flex flex-col gap-8 py-10 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <img
              src={theme === "dark" ? "/assets/logos/emc-logo-dark.png" : "/assets/logos/emc-logo.png"}
              alt="Event Management Club"
              className="h-11 w-11 object-contain"
            />
            <div>
              <p className="font-serif text-xl">EMC Veritas</p>
              <p className="text-[10px] font-semibold tracking-[.12em] text-slate-400">
                EVENT MANAGEMENT CLUB · NFC-IET MULTAN
              </p>
              <p className="landing-footer-note">Student recognition archive · issued by EMC</p>
            </div>
          </div>
          <div className="landing-footer-links flex gap-6 text-sm text-slate-300">
            <a href="#how-it-works">How it works</a>
            <a href="#document-types">Document types</a>
            <Link to="/verify">Verify</Link>
          </div>
          <div className="landing-nfc-mark"><img src="/assets/logos/nfc-iet-logo.png" alt="NFC-IET Multan" className="h-12 w-12 object-contain" /><span>NFC-IET<br />MULTAN</span></div>
        </div>
      </footer>
      {adminRollNumber && (
        <AdminLoginModal
          rollNumber={adminRollNumber}
          onSubmit={login}
          onClose={() => setAdminRollNumber(null)}
        />
      )}
    </main>
  );
}
