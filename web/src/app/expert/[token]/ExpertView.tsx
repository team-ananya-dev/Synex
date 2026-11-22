"use client";

// Expert page: opened from the private link in an approved outreach email. A teammate answers here
// in the persona of the candidate. It never shows the customer, other experts or contact details.
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ATTESTATIONS, type AnswerKind, type Confidence, type ExpertPage } from "@/lib/api";

type Draft = { kind: AnswerKind; text: string; confidence: Confidence | null };

const RULES = [
  "Do not share anything confidential.",
  "Do not share anything covered by a non-disclosure agreement.",
  "Do not share non-public information about the company's finances.",
];

export function ExpertView() {
  const { token } = useParams<{ token: string }>();
  const [page, setPage] = useState<ExpertPage | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.getExpertPage(token).then(setPage).catch((e) => setLoadError(e.message));
  }, [token]);

  if (loadError) return <Closed message={loadError.startsWith("404") ? "This link is not valid." : loadError} />;
  if (!page) return <p className="text-sm text-zinc-500">Loading…</p>;
  if (!page.available) return <Closed message={page.reason} />;
  if (done || page.submitted) {
    return (
      <Closed
        title="Thank you"
        message="Your answers were received. Each one is screened before it is used; you are told which answers were accepted. Payout is simulated."
      />
    );
  }

  const draft = (i: number): Draft => drafts[i] ?? { kind: "answer", text: "", confidence: null };
  const setDraft = (i: number, patch: Partial<Draft>) => setDrafts((d) => ({ ...d, [i]: { ...draft(i), ...patch } }));
  const allTicked = ATTESTATIONS.every(([key]) => ticks[key]);
  const complete = page.subquestions.every((s) => {
    const d = draft(s.index);
    return d.kind !== "answer" || (d.text.trim().length >= 2 && d.confidence);
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!page?.available) return;
    setBusy(true);
    setError(null);
    try {
      await api.submitResponses(token, {
        mode: "form",
        attestations: ticks,
        answers: page.subquestions.map((s) => ({ index: s.index, ...draft(s.index) })),
      });
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const { persona } = page;

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-8">
      <section className="space-y-2">
        <h1 className="text-2xl font-semibold">{page.first_name ? `Hello ${page.first_name},` : "Hello,"}</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Synex is a research service. We are asking a few former employees short questions about their first-hand
          experience. We found you through your public professional profile. Your name is never shown to the person
          who asked the question.
        </p>
        <p className="rounded-md bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
          Answering as: <strong>{persona.role ?? "former employee"}</strong>
          {persona.company && <> at <strong>{persona.company}</strong></>}
          {persona.tenure_months != null && <> ({persona.tenure_months} months)</>}
        </p>
      </section>

      <section className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950/40">
        <h2 className="font-semibold">Ground rules</h2>
        <ul className="list-disc space-y-1 pl-5">
          {RULES.map((r) => <li key={r}>{r}</li>)}
        </ul>
        <p>
          Every answer is screened before it is used. Answers that contain confidential information are rejected and
          not paid. Payout: <strong>${page.payout.per_accepted_answer.toFixed(2)}</strong> per accepted answer (
          {page.payout.currency}; no money moves).
        </p>
      </section>

      <section className="space-y-6">
        {page.subquestions.map((s) => {
          const d = draft(s.index);
          return (
            <fieldset key={s.index} className="space-y-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
              <legend className="px-1 text-sm font-medium">Question {s.index}</legend>
              <p className="text-sm">{s.text}</p>
              <div className="flex flex-wrap gap-4 text-sm">
                {([
                  ["answer", "I can answer"],
                  ["dont_know", "I don't know"],
                  ["confidential", "I can't answer without sharing confidential information"],
                ] as [AnswerKind, string][]).map(([kind, label]) => (
                  <label key={kind} className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      name={`kind-${s.index}`}
                      checked={d.kind === kind}
                      onChange={() => setDraft(s.index, { kind })}
                    />
                    {label}
                  </label>
                ))}
              </div>
              {d.kind === "answer" && (
                <>
                  <textarea
                    value={d.text}
                    onChange={(e) => setDraft(s.index, { text: e.target.value })}
                    rows={5}
                    maxLength={6000}
                    placeholder="Your answer, from your own experience. Ranges and trends are better than exact internal figures."
                    className="w-full rounded-md border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700"
                  />
                  <label className="flex items-center gap-2 text-sm">
                    How confident are you?
                    <select
                      value={d.confidence ?? ""}
                      onChange={(e) => setDraft(s.index, { confidence: (e.target.value || null) as Confidence | null })}
                      className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                    >
                      <option value="">choose</option>
                      <option value="low">low</option>
                      <option value="medium">medium</option>
                      <option value="high">high</option>
                    </select>
                  </label>
                </>
              )}
            </fieldset>
          );
        })}
      </section>

      <section className="space-y-2 text-sm">
        <h2 className="font-semibold">Before you submit, confirm</h2>
        {ATTESTATIONS.map(([key, label]) => (
          <label key={key} className="flex items-start gap-2">
            <input
              type="checkbox"
              className="mt-1"
              checked={!!ticks[key]}
              onChange={(e) => setTicks((t) => ({ ...t, [key]: e.target.checked }))}
            />
            {label}
          </label>
        ))}
      </section>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy || !allTicked || !complete}
          className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
        >
          {busy ? "Submitting…" : "Submit answers"}
        </button>
        <span className="text-xs text-zinc-500">Answers cannot be changed after you submit.</span>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}

function Closed({ title = "Not available", message }: { title?: string; message: string }) {
  return (
    <div className="mx-auto max-w-xl space-y-2 py-10 text-center">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{message}</p>
    </div>
  );
}
