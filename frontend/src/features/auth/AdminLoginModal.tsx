import { FormEvent, useState } from "react";

type AdminLoginModalProps = {
  rollNumber: string;
  onSubmit: (password: string) => Promise<void>;
  onClose: () => void;
};

export function AdminLoginModal({
  rollNumber,
  onSubmit,
  onClose,
}: AdminLoginModalProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(password);
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
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4"
      role="presentation"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-login-title"
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="admin-login-title" className="text-xl font-bold">
              Admin sign in
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Continue as {rollNumber}.
            </p>
          </div>
          <button
            type="button"
            className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={onClose}
            aria-label="Close sign in"
          >
            ×
          </button>
        </div>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium" htmlFor="admin-password">
            Password
            <input
              id="admin-password"
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <p
              role="alert"
              className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300"
            >
              {error}
            </p>
          )}
          <button
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
