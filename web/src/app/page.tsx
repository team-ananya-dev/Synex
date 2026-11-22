"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type CaseSummary } from "@/lib/api";
import { StateBadge } from "@/components/StateBadge";

export default function AskPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

  useEffect(() => {
    api.listCases().then(setCases).catch((e) => setError(`Could not reach the server: ${e.message}`));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createCase(question.trim());
      router.push(`/cases/${created.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const tooShort = question.trim().length < 5;

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">Ask a business question</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Synex splits the question into sub-questions, finds former employees who can answer them, screens everyone
          against fixed compliance rules, and writes a memo where every claim cites its source.
        </p>
        <form onSubmit={submit} className="space-y-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            rows={4}
            placeholder="For example: how are unit economics trending in quick commerce in India?"
            className="w-full rounded-md border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={busy || tooShort}
              className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
            >
              {busy ? "Starting…" : "Start research"}
            </button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Recent cases</h2>
        {cases === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : cases.length === 0 ? (
          <p className="text-sm text-zinc-500">No cases yet.</p>
        ) : (
          <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
            {cases.map((c) => (
              <li key={c.id}>
                <Link href={`/cases/${c.id}`} className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900">
                  <StateBadge state={c.state} />
                  <span className="flex-1 truncate">{c.question}</span>
                  <time className="text-xs text-zinc-500">{new Date(c.created_at).toLocaleString()}</time>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
