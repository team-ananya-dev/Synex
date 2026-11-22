"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type CaseSummary } from "@/lib/api";
import { StateBadge } from "@/components/StateBadge";

// Example questions only fill the text box; nothing about them is special-cased anywhere.
const EXAMPLES = [
  "How are unit economics trending in quick commerce in India?",
  "How do mid-size SaaS companies price enterprise plans, and how has that changed?",
  "What is driving customer churn at consumer fintech apps?",
];

export default function AskPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

  useEffect(() => {
    api.listCustomerCases().then(setCases).catch((e) => setError(`Could not reach the server: ${e.message}`));
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

  const disabled = busy || question.trim().length < 5;

  return (
    <div className="flex flex-col gap-11">
      <form onSubmit={submit} className="flex max-w-[780px] flex-col gap-4">
        <h1 className="text-[28px] font-semibold tracking-[-.02em]">Ask a business question</h1>
        <p className="text-[15px] leading-relaxed text-pretty text-zinc-400">
          Synex splits the question into sub-questions, finds former employees who can answer them, screens everyone
          against fixed compliance rules, and writes a memo where every claim cites its source.
        </p>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={2000}
          rows={4}
          placeholder="For example: how are unit economics trending in quick commerce in India?"
          className="w-full resize-y rounded-lg border border-zinc-700 bg-panel px-4 py-3.5 text-base leading-normal outline-none focus:border-zinc-500"
        />
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((x) => (
            <button
              key={x}
              type="button"
              onClick={() => setQuestion(x)}
              className="max-w-full truncate rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-400 hover:text-foreground"
            >
              {x}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3.5">
          <button
            type="submit"
            disabled={disabled}
            className="rounded-md bg-foreground px-4 py-[9px] text-sm font-medium text-background disabled:opacity-40"
          >
            {busy ? "Starting…" : "Start research"}
          </button>
          <span className="text-[13px] text-zinc-500">
            Questions asking for non-public information are refused or rewritten, with the reason shown.
          </span>
        </div>
        {error && <p className="text-[13px] text-red-300">{error}</p>}
      </form>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Recent cases</h2>
        {cases === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : cases.length === 0 ? (
          <p className="text-sm text-zinc-500">No cases yet.</p>
        ) : (
          <div className="flex flex-col overflow-hidden rounded-lg border border-zinc-800">
            {cases.map((c, i) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className={`flex items-center gap-3 px-4 py-3 text-sm hover:bg-hover ${i ? "border-t border-zinc-800" : ""}`}
              >
                <StateBadge state={c.state} wide />
                <span className="min-w-0 flex-1 truncate">{c.question}</span>
                <span className="font-mono text-xs text-zinc-500">{c.id}</span>
                <span className="min-w-28 text-right text-xs text-zinc-500">{new Date(c.created_at).toLocaleString()}</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
