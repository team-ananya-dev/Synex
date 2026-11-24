"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, serverKeys, setUserKeys, userKeys, type CaseSummary, type ServerKeys } from "@/lib/api";
import { StateBadge } from "@/components/StateBadge";

// Example questions only fill the text box; nothing about them is special-cased anywhere.
const EXAMPLES = [
  "How does Zepto run dark store operations and rider logistics compared with Blinkit?",
  "How do Delhivery and Ecom Express handle return-to-origin parcels for e-commerce sellers?",
  "What are warehouse managers at Indian 3PL firms like Mahindra Logistics seeing in labour costs and automation?",
  "How has Shiprocket's courier aggregation changed for small online sellers over the last two years?",
  "How are unit economics trending in quick commerce in India?",
  "How do mid-size SaaS companies price enterprise plans, and how has that changed?",
  "What is driving customer churn at consumer fintech apps?",
  "What revenue will Zepto report in its next unannounced funding round?",
];

// The landing page's DIVE button sends the typed question as ?q=; reading it needs a Suspense boundary.
export default function AskPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading…</p>}>
      <AskForm />
    </Suspense>
  );
}

function AskForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [question, setQuestion] = useState(() => params.get("q") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [mine, setMine] = useState(userKeys);
  const [server, setServer] = useState<ServerKeys | null>(null);   // keys the server already has (a local clone with .env)

  useEffect(() => {
    serverKeys().then(setServer);
  }, []);
  const needAnthropic = server !== null && !server.anthropic && !mine.anthropic.trim();
  const needCrustdata = server !== null && !server.crustdata && !mine.crustdata.trim();

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

  const disabled = busy || question.trim().length < 5 || needAnthropic || needCrustdata;
  const showKeys = server !== null && (!server.anthropic || !server.crustdata);
  const update = (k: Partial<typeof mine>) => {
    const next = { ...mine, ...k };
    setMine(next);
    setUserKeys(next);
  };

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
        {showKeys && (
          <fieldset className="flex flex-col gap-3 rounded-lg border border-zinc-800 p-4">
            <legend className="px-1 text-sm font-medium">Your API keys</legend>
            <p className="text-[13px] leading-relaxed text-zinc-400">
              This site runs on your own keys, so the research is billed to your accounts. They stay in this browser tab
              (cleared when you close it) and are sent only with your requests. The server keeps them in memory while your
              case runs and never saves them.
            </p>
            {!server.anthropic && (
              <label className="flex flex-col gap-1 text-[13px] text-zinc-400">
                Anthropic API key
                <input
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={mine.anthropic}
                  onChange={(e) => update({ anthropic: e.target.value })}
                  placeholder="sk-ant-..."
                  className="rounded-md border border-zinc-700 bg-panel px-3 py-2 font-mono text-sm text-foreground outline-none focus:border-zinc-500"
                />
              </label>
            )}
            {!server.crustdata && (
              <label className="flex flex-col gap-1 text-[13px] text-zinc-400">
                Crustdata API key
                <input
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={mine.crustdata}
                  onChange={(e) => update({ crustdata: e.target.value })}
                  className="rounded-md border border-zinc-700 bg-panel px-3 py-2 font-mono text-sm text-foreground outline-none focus:border-zinc-500"
                />
              </label>
            )}
          </fieldset>
        )}
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
