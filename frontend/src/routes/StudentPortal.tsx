import { FormEvent, type ReactNode, useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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

const journey = [
  { stage: "Event", value: 28 },
  { stage: "Certificate", value: 52 },
  { stage: "Recognition", value: 74 },
  { stage: "Verified", value: 100 },
];
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
    <div className="recognition-canvas" aria-label="EMC Veritas recognition experience">
      <motion.div className="recognition-orbit recognition-orbit--one" animate={{ rotate: 360 }} transition={{ duration: 38, ease: "linear", repeat: Infinity }} />
      <motion.div className="recognition-orbit recognition-orbit--two" animate={{ rotate: -360 }} transition={{ duration: 29, ease: "linear", repeat: Infinity }} />
      <motion.div className="recognition-ticket" initial={{ opacity: 0, y: 28, rotate: -7 }} animate={{ opacity: 1, y: 0, rotate: -4 }} transition={{ duration: .8, delay: .15 }}>
        <p>EMC VERITAS · NFC-IET MULTAN</p><strong>Recognition, made tangible.</strong><span>YOUR CONTRIBUTION DESERVES A LASTING RECORD</span>
      </motion.div>
      <motion.div className="recognition-certificate" initial={{ opacity: 0, y: 36, rotate: 5 }} animate={{ opacity: 1, y: 0, rotate: 2 }} transition={{ duration: .9, delay: .25 }}>
        <div className="recognition-certificate__top"><img src="/assets/logos/emc-logo-dark.png" alt="" /><span>EMC VERITAS</span></div>
        <p className="recognition-certificate__eyebrow">OFFICIAL RECOGNITION</p>
        <h2>Certificate of<br />Participation</h2><div className="recognition-line" /><p className="recognition-name">Your story, recognised.</p>
        <div className="recognition-certificate__footer"><span>Authentic record</span><VeritasSeal small /></div>
      </motion.div>
      <motion.div className="recognition-stamp" animate={{ y: [0, -9, 0] }} transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}><Shield /><span>VERIFIED<br />BY EMC</span></motion.div>
    </div>
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
function SectionTitle({
  eyebrow,
  title,
  copy,
}: {
  eyebrow: string;
  title: string;
  copy?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="landing-eyebrow">{eyebrow}</p>
      <h2 className="landing-title mt-3">{title}</h2>
      {copy && (
        <p className="mt-4 text-base leading-7 text-slate-300">{copy}</p>
      )}
    </div>
  );
}
function RecognitionChart() {
  return (
    <div
      className="mt-7 h-36 w-full"
      aria-label="Illustration of a personal recognition journey"
    >
      <ResponsiveContainer>
        <AreaChart
          data={journey}
          margin={{ top: 8, right: 6, left: -26, bottom: 0 }}
        >
          <defs>
            <linearGradient id="journeyGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#c92b45" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#c92b45" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="stage"
            tick={{ fill: "#d9ddeb", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide domain={[0, 105]} />
          <Tooltip cursor={false} contentStyle={{ display: "none" }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#e8b96c"
            strokeWidth={2}
            fill="url(#journeyGradient)"
            isAnimationActive
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StudentPortal() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
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
            <span className="mt-0.5 block text-[8px] font-semibold tracking-[.16em] text-slate-300">
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
          <a href="#document-lookup" className="landing-login-link">
            Admin sign in <Arrow />
          </a>
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
            <p className="landing-eyebrow">Student recognition portal</p>
            <h1 className="landing-hero-title mt-5">
              Your achievements,
              <br />
              <em>officially recognised.</em>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-200">
              Enter your roll number to find certificates and recognition
              letters earned through EMC.
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
                {checkingLookup ? "Checking…" : "Find my documents"}
                <Arrow />
              </Button>
            </form>
            <p className="mt-4 text-xs tracking-[.14em] text-slate-400">
              YOUR EFFORTS CREATE A BRIGHTER CAMPUS
            </p>
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
      <div className="landing-marquee" aria-hidden="true"><div>EMC VERITAS <i>✦</i> RECOGNITION THAT LASTS <i>✦</i> YOUR WORK HAS A STORY <i>✦</i> EMC VERITAS <i>✦</i> RECOGNITION THAT LASTS</div></div>
      <section id="document-types" className="landing-shell py-20">
        <SectionTitle
          eyebrow="What you can find here"
          title="Recognition that stays with you."
          copy="Every record is organised in one official place—ready whenever you need it."
        />
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            [
              "Participation certificates",
              "Official proof of your valuable participation in EMC events and activities.",
              "Participation",
            ],
            [
              "Appreciation certificates",
              "Recognition for your dedication and meaningful contribution to EMC.",
              "Appreciation",
            ],
            [
              "Leadership recognition",
              "Recognition letters for leadership roles and exceptional commitment.",
              "Leadership",
            ],
          ].map(([title, copy, type], index) => (
            <motion.article
              key={title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              whileHover={{ y: -8, transition: { duration: 0.22 } }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ delay: index * 0.1 }}
              className="landing-document-card"
            >
              <div className="certificate-mini">
                <p>EMC Veritas</p>
                <strong>{type}</strong>
                <VeritasSeal small />
              </div>
              <h3>{title}</h3>
              <p>{copy}</p>
              <button type="button" onClick={scrollToLookup}>
                Find yours <Arrow />
              </button>
            </motion.article>
          ))}
        </div>
      </section>
      <section className="landing-shell py-7">
        <div className="landing-journey grid overflow-hidden rounded-3xl border border-white/10 p-7 md:grid-cols-[1.1fr_.9fr] md:p-10">
          <div>
            <p className="landing-eyebrow">Your recognition journey</p>
            <h2 className="landing-title mt-3 text-4xl">
              A timeline worth keeping.
            </h2>
            <p className="mt-4 max-w-lg leading-7 text-slate-300">
              From taking part in an event to receiving official recognition,
              Veritas keeps your achievements connected.
            </p>
            <RecognitionChart />
          </div>
          <div className="relative mt-8 hidden min-h-56 md:mt-0 md:block">
            <div className="absolute inset-8 rotate-6 rounded border border-[#e5bf79]/45 bg-[#ede2c5] shadow-2xl" />
            <div className="absolute inset-x-4 inset-y-4 -rotate-3 rounded border border-[#e5bf79]/60 bg-[#fbf4e5] p-7 text-[#402d2a] shadow-2xl">
              <p className="text-[10px] tracking-[.17em]">EMC VERITAS</p>
              <p className="mt-8 font-serif text-3xl leading-tight">
                Recognition builds brighter futures.
              </p>
              <div className="absolute bottom-5 right-6">
                <VeritasSeal small />
              </div>
            </div>
          </div>
        </div>
      </section>
      <section id="how-it-works" className="landing-shell py-24">
        <SectionTitle
          eyebrow="Simple steps · lasting recognition"
          title="Find your recognition in seconds."
        />
        <div className="landing-steps-shell mt-12 grid gap-4 md:grid-cols-3">
          {[
            [
              "1",
              "Enter your roll number",
              "Type your roll number to access your personal records.",
              <FileIcon />,
            ],
            [
              "2",
              "View your recognised achievements",
              "See all your certificates and recognition letters in one place.",
              <Spark />,
            ],
            [
              "3",
              "Download or verify anytime",
              "Download your documents or share them for verification whenever you need.",
              <Shield />,
            ],
          ].map(([number, title, copy, icon]) => (
            <motion.div
              key={String(number)}
              className="landing-step"
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={{ delay: Number(number) * 0.08 }}
            >
              <span>{number}</span>
              <div className="landing-step-icon">{icon as ReactNode}</div>
              <h3>{title}</h3>
              <p>{copy}</p>
            </motion.div>
          ))}
        </div>
      </section>
      <section id="verify" className="landing-shell pb-24">
        <Link
          to="/verify"
          className="landing-verify grid items-center gap-8 rounded-3xl border border-[#e7c577]/20 p-7 md:grid-cols-[auto_1fr] md:p-10"
        >
          <VerificationMark />
          <div>
            <p className="landing-eyebrow">Verify a document</p>
            <h2 className="landing-title mt-3 text-4xl">
              Official. Verifiable. Yours.
            </h2>
            <p className="mt-4 max-w-2xl leading-7 text-slate-300">
              Every certificate and recognition letter issued through EMC
              Veritas has a unique verification record, making it easy to
              confirm its authenticity.
            </p>
            <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#e8c172]">
              Open document verification <Arrow />
            </span>
          </div>
        </Link>
      </section>
      <section className="landing-closing">
        <div className="landing-shell landing-closing__inner">
          <p className="landing-eyebrow">EMC Veritas archive</p>
          <p className="landing-closing__quote">The work you show up for today<br /><em>deserves to be remembered tomorrow.</em></p>
          <VeritasSeal />
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
              <p className="text-[8px] font-semibold tracking-[.14em] text-slate-400">
                EVENT MANAGEMENT CLUB · NFC-IET MULTAN
              </p>
            </div>
          </div>
          <div className="flex gap-6 text-sm text-slate-300">
            <a href="#how-it-works">How it works</a>
            <a href="#document-types">Document types</a>
            <Link to="/verify">Verify</Link>
          </div>
          <img
            src="/assets/logos/nfc-iet-logo.png"
            alt="NFC-IET Multan"
            className="h-12 w-12 object-contain"
          />
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
