"use client";

// Customer screen. Uses only /customer routes, which never carry a name, headline,
// profile link, city or email (contracts/API.md, customer routes).
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, type CustomerCase, type ExpertCard, type SubQuestion, type SynexEvent } from "@/lib/api";
import { useCaseEvents } from "@/lib/useCaseEvents";
import { StateBadge } from "@/components/StateBadge";

const STAGES: [string, string][] = [
  ["s1_question_screen", "Question screen"],
  ["s2_decomposer", "Plan"],
  ["s3_sourcer", "Sourcing"],
  ["s4_people_screen", "People screen"],
  ["s5_ranker", "Ranking"],
  ["s5b_enrich_rerank", "Enrich and re-rank"],
  ["s6_outreach_writer", "Outreach drafts"],
];

// Events that change what GET /customer/cases/{id} returns; refetch when one arrives.
const REFRESH_ON = new Set([
  "case.state", "plan.approved", "stage.done", "stage.failed", "llm.call", "crustdata.call", "job.paused",
  "approval.approved", "approval.rejected", "mail.sent", "mail.blocked", "mail.failed",
  "ledger.hold", "ledger.capture", "ledger.release",
]);

const money = (n: number) => `$${n.toFixed(2)}`;

export function CaseView() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CustomerCase | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.getCustomerCase(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);
  const onEvent = useCallback((e: SynexEvent) => REFRESH_ON.has(e.type) && load(), [load]);
  const { events, connected } = useCaseEvents(id, "customer", onEvent);

  if (error && !data) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-zinc-500">Loading case…</p>;

  const done = new Set(events.filter((e) => e.type === "stage.done").map((e) => e.stage as string));
  const started = new Set(events.filter((e) => e.type === "stage.started").map((e) => e.stage as string));
  const failed = events.find((e) => e.type === "stage.failed");
  const rewrite = events.find((e) => e.type === "stage.done" && e.stage === "s1_question_screen")?.result as
    | { verdict: string; reason: string; effective_question: string }
    | undefined;
  const sourcing = events.find((e) => e.type === "stage.done" && e.stage === "s3_sourcer")?.result as
    | Record<string, { companies: { asked: string; resolved: boolean; name: string | null; total_matches: number | null }[]; found: number }>
    | undefined;

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <StateBadge state={data.state} />
          <span className={`text-xs ${connected ? "text-emerald-600" : "text-zinc-500"}`}>
            {connected ? "● live" : "○ reconnecting"}
          </span>
          <span className="ml-auto text-xs text-zinc-500">case {data.id}</span>
        </div>
        <h1 className="text-xl font-semibold">{data.question}</h1>
        {rewrite?.verdict === "rewrite" && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            Rewritten for compliance: “{rewrite.effective_question}” ({rewrite.reason})
          </p>
        )}
        {data.state === "REFUSED" && (
          <Alert>Refused by the question screen: {data.refusal_reason}</Alert>
        )}
        {failed && <Alert>Stage {String(failed.stage)} failed: {String(failed.error)}</Alert>}
      </section>

      <section className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <Counter label="Crustdata credits" value={`${data.cost.crustdata_credits.toFixed(1)} / ${data.cost.credit_cap}`} />
        <Counter label="Model spend" value={`$${data.cost.model_usd.toFixed(4)}`} />
        <Counter label="Held (simulated)" value={money(data.ledger.balance.remaining)} />
        <Counter label="Charged (simulated)" value={money(data.ledger.balance.captured)} />
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Progress</h2>
        <ol className="flex flex-wrap gap-2 text-xs">
          {STAGES.map(([key, label]) => {
            const state = failed?.stage === key ? "failed" : done.has(key) ? "done" : started.has(key) ? "running" : "waiting";
            return (
              <li key={key} className={`rounded px-2 py-1 ${STAGE_STYLE[state]}`}>
                {label} · {state}
              </li>
            );
          })}
        </ol>
        <OutreachLine outreach={data.outreach} />
      </section>

      {data.state === "PLANNED" && data.quote && <PlanApproval data={data} onApproved={load} />}

      {data.plan && data.plan.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Research plan and panel</h2>
          {data.plan.map((sq) => (
            <SubQuestionCard key={sq.index} sq={sq} data={data} sourcing={sourcing?.[String(sq.index)]} />
          ))}
        </section>
      )}

      {data.ledger.entries.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">Ledger <span className="text-sm font-normal text-zinc-500">(simulated, no money moves)</span></h2>
          <table className="w-full text-sm">
            <tbody>
              {data.ledger.entries.map((e, i) => (
                <tr key={i} className="border-t border-zinc-200 dark:border-zinc-800">
                  <td className="py-1.5 font-mono text-xs">{e.kind}</td>
                  <td className="py-1.5 font-mono">{money(e.amount)}</td>
                  <td className="py-1.5 text-zinc-600 dark:text-zinc-400">{e.note}</td>
                  <td className="py-1.5 text-right text-xs text-zinc-500">{new Date(e.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function PlanApproval({ data, onApproved }: { data: CustomerCase; onApproved: () => void }) {
  const quote = data.quote!;
  const [panelSize, setPanelSize] = useState(3);
  const [budget, setBudget] = useState(String(quote.hold_amount));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      await api.approvePlan(data.id, panelSize, Number(budget));
      onApproved();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-md border border-sky-300 bg-sky-50 p-4 text-sm dark:border-sky-900 dark:bg-sky-950/40">
      <h2 className="text-lg font-semibold">Approve the plan to start finding experts</h2>
      <p>
        Quote: {quote.subquestions} sub-question{quote.subquestions === 1 ? "" : "s"} × {money(quote.price_per_subquestion)} ={" "}
        <strong>{money(quote.hold_amount)}</strong> held ({quote.currency}). You are charged only for sub-questions that get
        answered; the rest is released. No expert data is fetched until you approve.
      </p>
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-zinc-600 dark:text-zinc-400">Experts per sub-question</span>
          <select
            value={panelSize}
            onChange={(e) => setPanelSize(Number(e.target.value))}
            className="rounded border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
          >
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-zinc-600 dark:text-zinc-400">Budget cap (simulated USD)</span>
          <input
            type="number"
            min={quote.hold_amount}
            step="any"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            className="w-32 rounded border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <button
          onClick={approve}
          disabled={busy || !(Number(budget) > 0)}
          className="rounded-md bg-foreground px-4 py-2 font-medium text-background disabled:opacity-40"
        >
          {busy ? "Approving…" : "Approve plan and place hold"}
        </button>
      </div>
      {error && <p className="text-red-600">{error}</p>}
    </section>
  );
}

const STAGE_STYLE: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  running: "bg-sky-100 text-sky-800 animate-pulse dark:bg-sky-950 dark:text-sky-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  waiting: "bg-zinc-100 text-zinc-500 dark:bg-zinc-900",
};

function Alert({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
      {children}
    </p>
  );
}

function Counter({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="font-mono text-base">{value}</div>
    </div>
  );
}

function OutreachLine({ outreach }: { outreach: CustomerCase["outreach"] }) {
  const parts = Object.entries(outreach).filter(([, n]) => n);
  if (!parts.length) return null;
  return (
    <p className="mt-2 text-xs text-zinc-500">
      Outreach: {parts.map(([status, n]) => `${n} ${status.toLowerCase()}`).join(" · ")}
    </p>
  );
}

function SubQuestionCard({
  sq, data, sourcing,
}: {
  sq: SubQuestion;
  data: CustomerCase;
  sourcing?: { companies: { asked: string; resolved: boolean; name: string | null; total_matches: number | null }[]; found: number };
}) {
  const idx = String(sq.index);
  const screening = data.screening[idx];
  const panel = data.panel[idx];

  return (
    <div className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex gap-2">
        <span className="font-mono text-sm text-zinc-500">{sq.index}.</span>
        <div className="flex-1 space-y-1">
          <p className="font-medium">{sq.text}</p>
          <p className="text-xs text-zinc-500">
            Expertise: {sq.expertise} · Companies: {sq.target_companies.map((c) => `${c.name} (${c.basis})`).join(", ")}
          </p>
        </div>
      </div>

      {(sourcing || screening) && (
        <p className="mt-3 text-xs text-zinc-500">
          {sourcing?.companies.map((c) =>
            c.resolved ? `${c.name}: ${c.total_matches ?? "?"} matches` : `${c.asked}: not found in Crustdata`,
          ).join(" · ")}
          {screening && ` · ${screening.considered} screened: ${screening.pass} passed, ${screening.review} need review, ${screening.fail} excluded`}
        </p>
      )}

      {panel && panel.length === 0 && (
        <p className="mt-3 text-sm text-amber-700 dark:text-amber-400">
          No candidate passed the screen and the relevance cut-off for this sub-question.
        </p>
      )}

      {panel && panel.length > 0 && (
        <ul className="mt-3 space-y-2">
          {panel.map((c) => <ExpertCardRow key={c.ref} c={c} />)}
        </ul>
      )}

      {screening && screening.excluded.length > 0 && (
        <details className="mt-3 text-xs text-zinc-500">
          <summary className="cursor-pointer">Why {screening.excluded.length} people were excluded</summary>
          <ul className="mt-2 space-y-1">
            {screening.excluded.map((x) => (
              <li key={x.ref}><span className="font-mono">{x.ref}</span>: {x.reasons.join("; ")}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ExpertCardRow({ c }: { c: ExpertCard }) {
  return (
    <li className="rounded border border-zinc-100 p-3 text-sm dark:border-zinc-900">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-zinc-500">{c.ref}</span>
        <span className="font-medium">{c.role ?? "Former employee"}</span>
        {c.company && <span className="text-zinc-500">· {c.company}</span>}
        {c.tenure_months != null && <span className="text-zinc-500">· {c.tenure_months} months</span>}
        {c.left_year && <span className="text-zinc-500">· left {c.left_year}</span>}
        {c.country && <span className="text-zinc-500">· {c.country}</span>}
        <span className="ml-auto font-mono">{c.score}</span>
        <span className="rounded bg-zinc-100 px-1.5 text-xs dark:bg-zinc-800">{c.fit}</span>
      </div>
      <p className="mt-1 text-zinc-600 dark:text-zinc-400">{c.reason}</p>
      {(c.evidence.length > 0 || c.evidence_hidden > 0) && (
        <p className="mt-1 text-xs text-zinc-500">
          {c.evidence.length > 0 && <>Evidence: {c.evidence.map((e) => `“${e}”`).join(", ")}</>}
          {c.evidence_hidden > 0 && <> {c.evidence.length > 0 && "· "}{c.evidence_hidden} more signal{c.evidence_hidden === 1 ? "" : "s"} from the profile summary</>}
        </p>
      )}
    </li>
  );
}
