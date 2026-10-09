import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { authApi } from "../features/auth/contracts";
import { canonicalRollNumber } from "../lib/utils";

export function AdminLogin() {
  const navigate = useNavigate();
  const session = useQuery({
    queryKey: ["admin", "session"],
    queryFn: authApi.currentSession,
    retry: false,
  });
  const [rollNumber, setRollNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (session.data?.authenticated && session.data.role)
    return <Navigate to="/admin" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await authApi.login(rollNumber.trim(), password);
      if (!result.authenticated)
        throw new Error(
          "Unable to sign in. Check your credentials and try again.",
        );
      navigate("/admin", { replace: true });
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <section className="mx-auto mt-12 w-full max-w-md rounded-2xl border border-white/10 bg-slate-900/90 p-7 shadow-2xl">
        <p className="text-xs font-bold tracking-[.16em] text-[#e8c172]">
          EMC VERITAS · ADMIN ACCESS
        </p>
        <h1 className="mt-3 font-serif text-3xl">Admin sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Use your assigned admin roll number and password to manage EMC
          records.
        </p>
        <form className="mt-7 grid gap-4" onSubmit={submit}>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>
              Roll number{" "}
              <span className="text-red-500" aria-hidden="true">
                *
              </span>
            </span>
            <input
              required
              value={rollNumber}
              onChange={(event) =>
                setRollNumber(canonicalRollNumber(event.target.value))
              }
              autoComplete="username"
              className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white"
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            <span>
              Password{" "}
              <span className="text-red-500" aria-hidden="true">
                *
              </span>
            </span>
            <input
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white"
            />
          </label>
          <button
            disabled={submitting}
            className="mt-2 rounded-lg bg-[#a91f35] px-4 py-3 font-semibold text-white hover:bg-[#c3304b] disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        {error && (
          <p
            role="alert"
            className="mt-4 rounded-lg border border-red-400/40 bg-red-950/50 p-3 text-sm text-red-100"
          >
            {error}
          </p>
        )}
        <Link
          to="/"
          className="mt-6 inline-flex text-sm font-semibold text-[#e8c172] hover:underline"
        >
          Back to student records
        </Link>
      </section>
    </main>
  );
}
