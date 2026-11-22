"use client";

// Customer screen. Uses only /customer routes (never a name, headline, profile link, city or email)
// plus the per-case cost log, which holds call ids, purposes and costs only.
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  api, type CaseCosts, type CaseResult, type ResultSubQuestion, type CustomerCase, type CustomerResponses, type ExpertCard, type OutreachStatus, type SubQuestion,
  type SynexEvent,
} from "@/lib/api";
import { useCaseEvents } from "@/lib/useCaseEvents";
import { Pill, StateBadge, TONE } from "@/components/StateBadge";
import { CostTable } from "@/components/CostTable";

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
  "outreach.batch_approved", "response.received", "response.screened", "result.summary_written", "case.retried",
]);

type Tab = "plan" | "live" | "result" | "costs";
type SourcingSummary = Record<string, {
  companies: { asked: string; resolved: boolean; name: string | null; total_matches: number | null }[];
  found: number;
}>;

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const stageResult = <T,>(events: SynexEvent[], stage: string) =>
  events.findLast((e) => e.type === "stage.done" && e.stage === stage)?.result as T | undefined;

export function CaseView() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CustomerCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab | null>(null);

  const load = useCallback(() => {
    api.getCustomerCase(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);
  const onEvent = useCallback((e: SynexEvent) => REFRESH_ON.has(e.type) && load(), [load]);
  const { events, connected } = useCaseEvents(id, "customer", onEvent);

  if (error && !data) return <p className="text-sm text-zinc-400">Case not found or server unreachable: {error}</p>;
  if (!data) return <p className="text-sm text-zinc-500">Loading case…</p>;

  // default tab: plan until outreach is out, then live
  const current: Tab = tab ?? (data.outreach.SENT || data.state === "COLLECTING" ? "live" : "plan");
  // each stage shows its latest status, so a stage that failed and then finished on a retry shows done
  const stageStatus: Record<string, "running" | "done" | "failed"> = {};
  for (const e of events) {
    const st = e.stage as string | undefined;
    if (!st) continue;
    if (e.type === "stage.started") stageStatus[st] = "running";
    else if (e.type === "stage.done" || e.type === "stage.reused") stageStatus[st] = "done";
    else if (e.type === "stage.failed") stageStatus[st] = "failed";
  }
  const failed = data.state === "FAILED" ? events.findLast((e) => e.type === "stage.failed") : undefined;
  const screen = stageResult<{ verdict: string; reason: string; effective_question: string }>(events, "s1_question_screen");

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2.5">
        <div className="flex items-center gap-3 text-xs">
          <StateBadge state={data.state} />
          <span className={connected ? "text-emerald-400" : "text-zinc-500"}>{connected ? "● live" : "○ reconnecting"}</span>
          <span className="ml-auto font-mono text-zinc-500">case {data.id}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-[-.01em] text-pretty">{data.question}</h1>
        {screen?.verdict === "rewrite" && (
          <p className="text-sm text-amber-300">Rewritten for compliance: “{screen.effective_question}” ({screen.reason})</p>
        )}
        {screen?.verdict === "allow" && <p className="text-[13px] text-emerald-300">✓ Question screen: {screen.reason}</p>}
        {data.state === "REFUSED" && <Alert>Refused by the question screen: {data.refusal_reason}</Alert>}
        {data.state === "LIMIT_REACHED" && (
          <Alert>Stopped at a run limit: {String(events.findLast((e) => e.type === "case.state" && e.state === "LIMIT_REACHED")?.reason ?? "a limit was reached")}</Alert>
        )}
        {failed && <Alert>Stage {String(failed.stage)} failed: {String(failed.error)}</Alert>}
      </section>

      <section className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3">
        <Counter label="Crustdata credits" value={`${data.cost.crustdata_credits.toFixed(1)} / ${data.cost.credit_cap}`} />
        <Counter label="Model spend" value={`$${data.cost.model_usd.toFixed(4)} · ₹${data.cost.model_inr.toFixed(2)}`} />
        <Counter label="Measured cost of this job" value={`₹${data.cost.total_inr.toFixed(2)}`} />
        {data.quote && <Counter label="Quoted price · no payment taken" value={inr(data.quote.quoted_price_inr)} />}
      </section>

      <section className="flex flex-wrap gap-1.5 text-xs">
        {STAGES.map(([key, label]) => {
          const s = stageStatus[key] ?? "waiting";
          return <span key={key} className={`rounded px-2 py-1 ${STAGE_STYLE[s]}`}>{label} · {s}</span>;
        })}
      </section>

      <div className="flex gap-1 border-b border-zinc-800">
        {(["plan", "live", "result", "costs"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm capitalize ${current === t ? "border-foreground text-foreground" : "border-transparent text-zinc-500 hover:text-zinc-300"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {current === "plan" && <PlanTab data={data} events={events} onChanged={load} />}
      {current === "live" && <LiveTab data={data} events={events} />}
      {current === "result" && <ResultTab caseId={data.id} events={events} />}
      {current === "costs" && <CostsTab data={data} />}
    </div>
  );
}

const STAGE_STYLE: Record<string, string> = {
  done: TONE.emerald,
  running: `${TONE.sky} animate-pulse`,
  failed: TONE.red,
  waiting: "bg-hover text-zinc-500",
};

function Alert({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-red-900 bg-[#1c0606] p-3 text-sm text-red-300">{children}</p>;
}

function Counter({ label, value, amber = false }: { label: string; value: string; amber?: boolean }) {
  return (
    <div className={`flex flex-col gap-1 rounded-lg border px-3.5 py-3 ${amber ? "border-[#2a1d08] bg-[#120c04]" : "border-zinc-800"}`}>
      <span className={`text-xs ${amber ? "text-amber-300/80" : "text-zinc-500"}`}>{label}</span>
      <span className="font-mono text-[17px] font-medium">{value}</span>
    </div>
  );
}

// ---- Plan tab ---------------------------------------------------------------------------------

function PlanTab({ data, events, onChanged }: { data: CustomerCase; events: SynexEvent[]; onChanged: () => void }) {
  const plan = data.plan ?? [];
  if (!plan.length) {
    return <p className="text-sm text-zinc-500">{data.state === "REFUSED" ? "No plan: the question was refused." : "Planning…"}</p>;
  }
  if (data.state === "PLANNED" && data.quote) {
    return (
      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-2.5">
          <h2 className="mb-1 text-[17px] font-semibold">Research plan</h2>
          {plan.map((sq) => (
            <div key={sq.index} className="flex gap-2.5 rounded-lg border border-zinc-800 px-4 py-3.5">
              <span className="font-mono text-sm text-zinc-500">{sq.index}.</span>
              <div className="flex flex-1 flex-col gap-1.5">
                <span className="text-[15px] font-medium text-pretty">{sq.text}</span>
                <span className="text-xs leading-normal text-zinc-500">{planMeta(sq)}</span>
              </div>
            </div>
          ))}
          <p className="mt-1 text-xs text-zinc-500">No Crustdata credit has been spent yet. Sourcing starts after you approve.</p>
        </div>
        <ApproveCard data={data} onApproved={onChanged} />
      </div>
    );
  }
  const sourcing = stageResult<SourcingSummary>(events, "s3_sourcer");
  const waiting = !Object.keys(data.panel).length;
  return (
    <div className="flex flex-col gap-3.5">
      {data.invites.length > 0 && <ReviewInvitations data={data} onApproved={onChanged} />}
      {waiting && data.state === "SOURCING" && (
        <p className="text-sm text-zinc-500">Finding, screening and ranking former employees…</p>
      )}
      {plan.map((sq) => <SubQuestionCard key={sq.index} sq={sq} data={data} sourcing={sourcing?.[String(sq.index)]} />)}
    </div>
  );
}

const planMeta = (sq: SubQuestion) =>
  `Expertise: ${sq.expertise} · Companies: ${sq.target_companies.map((c) => `${c.name} (${c.basis})`).join(", ")}`;

function ApproveCard({ data, onApproved }: { data: CustomerCase; onApproved: () => void }) {
  const quote = data.quote!;
  const [panelSize, setPanelSize] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      await api.approvePlan(data.id, panelSize);
      onApproved();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3.5 rounded-[10px] border border-zinc-800 bg-panel p-[18px]">
      <span className="text-[15px] font-semibold">Approve the plan</span>
      <div className="flex flex-col gap-2 text-[13px]">
        <Row label="Sub-questions" value={String(quote.subquestions)} />
        <Row label="Per answered sub-question" value={inr(quote.price_per_subquestion_inr)} />
        <div className="h-px bg-zinc-800" />
        <div className="flex justify-between text-[15px]">
          <span>Quoted price</span>
          <span className="font-mono font-medium">{inr(quote.quoted_price_inr)}</span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5 text-[13px]">
        <span className="text-zinc-400">Experts contacted per sub-question</span>
        <div className="flex overflow-hidden rounded-md border border-zinc-800">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => setPanelSize(n)}
              className={`flex-1 py-[7px] text-[13px] ${panelSize === n ? "bg-foreground text-background" : "text-zinc-400 hover:bg-hover"}`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs leading-relaxed text-zinc-400">
        {quote.label[0].toUpperCase() + quote.label.slice(1)}. This build makes no payments; the price is shown for information.
      </p>
      {error && <span className="text-[13px] text-red-300">{error}</span>}
      <button
        onClick={approve}
        disabled={busy}
        className="rounded-md bg-foreground px-3.5 py-2.5 text-sm font-medium text-background disabled:opacity-40"
      >
        {busy ? "Approving…" : "Approve plan and start sourcing"}
      </button>
    </div>
  );
}

// The customer's approval of the anonymised invitations. Nothing is emailed before this click; each invitation is
// its own logged approval. The preview has no name, address or link.
function ReviewInvitations({ data, onApproved }: { data: CustomerCase; onApproved: () => void }) {
  const waiting = data.invites.filter((i) => i.status === "DRAFTED");
  const [chosen, setChosen] = useState<Set<string>>(() => new Set(waiting.filter((i) => i.selected_by_default).map((i) => i.ref)));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = (ref: string) =>
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(ref)) next.delete(ref);
      else next.add(ref);
      return next;
    });

  async function send() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.approveOutreach(data.id, [...chosen]);
      setResult(`${r.sent} sent · ${r.dropped} dropped${r.blocked ? ` · ${r.blocked} blocked` : ""}${r.failed ? ` · ${r.failed} failed` : ""}`);
      onApproved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-[10px] border border-zinc-800 bg-panel p-[18px]">
      <div className="flex items-baseline gap-2">
        <span className="text-[15px] font-semibold">{waiting.length ? "Review invitations" : "Invitations"}</span>
        <span className="text-xs text-zinc-500">
          {waiting.length
            ? "Tick the experts to invite. Nothing is sent before you approve. Flagged experts start unticked: read why."
            : "Approved. In this build every invitation goes to a teammate's inbox, never to a real person."}
        </span>
      </div>
      {data.invites.map((i) => (
        <div key={i.ref} className={`flex flex-col gap-2 rounded-lg border px-3.5 py-3 text-[13px] ${i.flagged ? "border-[#4a3510]" : "border-zinc-800"}`}>
          <label className="flex cursor-pointer flex-wrap items-center gap-2">
            {i.status === "DRAFTED" ? (
              <input type="checkbox" checked={chosen.has(i.ref)} onChange={() => toggle(i.ref)} />
            ) : (
              <Pill tone={i.status === "SENT" ? "emerald" : i.status === "REJECTED" ? "zinc" : "red"}>{i.status.toLowerCase()}</Pill>
            )}
            <span className="font-mono text-xs">{i.ref}</span>
            <span className="font-medium">{[i.role, i.company].filter(Boolean).join(" · ")}</span>
            {i.tenure_months != null && <span className="text-zinc-500">{i.tenure_months} months</span>}
            <span className="ml-auto text-xs text-zinc-500">sub-questions {i.subquestion_indices.join(", ")}</span>
          </label>
          {i.flagged && i.flag_reasons.map((r, k) => <span key={k} className="text-xs text-amber-300">⚑ {r}</span>)}
          <details>
            <summary className="cursor-pointer text-xs text-zinc-400">Preview: {i.subject}</summary>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-zinc-300">{i.preview}</pre>
          </details>
        </div>
      ))}
      {error && <span className="text-[13px] text-red-300">{error}</span>}
      {result && <span className="text-[13px] text-emerald-300">{result}</span>}
      {waiting.length > 0 && (
        <button
          onClick={send}
          disabled={busy || chosen.size === 0}
          className="self-start rounded-md bg-foreground px-3.5 py-2.5 text-sm font-medium text-background disabled:opacity-40"
        >
          {busy ? "Sending…" : `Approve and send ${chosen.size} invitation${chosen.size === 1 ? "" : "s"}`}
        </button>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-zinc-400">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}

function SubQuestionCard({ sq, data, sourcing }: { sq: SubQuestion; data: CustomerCase; sourcing?: SourcingSummary[string] }) {
  const idx = String(sq.index);
  const screening = data.screening[idx];
  const panel = data.panel[idx];
  const sourcedLine = [
    ...(sourcing?.companies.map((c) =>
      c.resolved ? `${c.name}: ${c.total_matches ?? "?"} matches` : `${c.asked}: not found in Crustdata`) ?? []),
    screening && `${screening.considered} screened: ${screening.pass} passed, ${screening.review} need review, ${screening.fail} excluded`,
  ].filter(Boolean).join(" · ");

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-800 p-4">
      <div className="flex gap-2.5">
        <span className="font-mono text-sm text-zinc-500">{sq.index}.</span>
        <div className="flex flex-1 flex-col gap-1">
          <span className="text-[15px] font-medium text-pretty">{sq.text}</span>
          <span className="text-xs text-zinc-500">{planMeta(sq)}</span>
        </div>
      </div>
      {sourcedLine && <span className="text-xs text-zinc-500">{sourcedLine}</span>}
      {panel && panel.length === 0 && (
        <span className="text-sm text-amber-300">No candidate passed the screen and the relevance cut-off.</span>
      )}
      {panel && panel.length > 0 && (
        <div className="flex flex-col gap-2">
          {panel.map((c) => <ExpertCardRow key={c.ref} c={c} />)}
        </div>
      )}
      {screening && screening.excluded.length > 0 && (
        <details className="text-xs text-zinc-500">
          <summary className="cursor-pointer">Why {screening.excluded.length} people were excluded</summary>
          <div className="mt-2 flex flex-col gap-1">
            {screening.excluded.map((x) => <span key={x.ref}><span className="font-mono">{x.ref}</span>: {x.reasons.join("; ")}</span>)}
          </div>
        </details>
      )}
    </div>
  );
}

function ExpertCardRow({ c }: { c: ExpertCard }) {
  const meta = [c.company, c.tenure_months != null && `${c.tenure_months} months`, c.left_year && `left ${c.left_year}`, c.country]
    .filter(Boolean).join(" · ");
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-line bg-sunken p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-zinc-800 px-1.5 py-px font-mono text-xs">{c.ref}</span>
        <span className="font-medium">{c.role ?? "Former employee"}</span>
        <span className="text-zinc-500">{meta}</span>
        <span className="ml-auto font-mono">{c.score}</span>
        <span className="rounded bg-zinc-800 px-1.5 text-xs">{c.fit}</span>
      </div>
      <span className="text-[13px] text-zinc-400">{c.reason}</span>
      {(c.evidence.length > 0 || c.evidence_hidden > 0) && (
        <span className="text-xs text-zinc-500">
          {c.evidence.length > 0 && <>Evidence: {c.evidence.map((e) => `“${e}”`).join(", ")}</>}
          {c.evidence_hidden > 0 && <>{c.evidence.length > 0 && " · "}{c.evidence_hidden} more signal{c.evidence_hidden === 1 ? "" : "s"} from the profile summary</>}
        </span>
      )}
    </div>
  );
}

// ---- Live tab ---------------------------------------------------------------------------------

const BOARD: [OutreachStatus | "ANSWERED", string, string][] = [
  ["DRAFTED", "awaiting approval", "text-amber-300"],
  ["SENT", "invited", "text-sky-300"],
  ["ANSWERED", "answers in", "text-violet-300"],
  ["REJECTED", "dropped", "text-zinc-400"],
  ["BLOCKED", "blocked", "text-red-300"],
  ["FAILED", "send failed", "text-red-300"],
];

const TARGET = 2; // accepted answers wanted per sub-question (independence is checked in the memo stage)

const VERDICT_TONE: Record<string, "emerald" | "sky" | "amber" | "red" | "zinc"> = {
  accepted: "emerald", redacted: "sky", held: "amber", rejected: "red", pending: "zinc",
};

function LiveTab({ data, events }: { data: CustomerCase; events: SynexEvent[] }) {
  const [screened, setScreened] = useState<CustomerResponses | null>(null);
  const responseEvents = events.filter((e) => e.type.startsWith("response.")).length;
  useEffect(() => {
    api.customerResponses(data.id).then(setScreened).catch(() => setScreened(null));
  }, [data.id, responseEvents]);

  const received = Object.values(screened?.coverage ?? {}).reduce((n, c) => n + c.received, 0);
  const counts: Record<string, number> = { ...data.outreach, ANSWERED: received };
  const plan = data.plan ?? [];

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2.5">
          <div className="flex items-baseline gap-2.5">
            <span className="text-[17px] font-semibold">Coverage</span>
            <span className="text-xs text-zinc-500">Target: {TARGET} accepted answers per sub-question</span>
          </div>
          <div className="flex flex-col rounded-lg border border-zinc-800">
            {plan.map((sq, i) => {
              const c = screened?.coverage[String(sq.index)];
              const ok = (c?.accepted ?? 0) + (c?.redacted ?? 0);
              const waiting = (c?.pending ?? 0) + (c?.held ?? 0);
              const label = ok >= TARGET ? "covered" : ok ? `${ok} of ${TARGET}` : waiting ? "screening" : "waiting";
              return (
                <div key={sq.index} className={`grid grid-cols-[22px_minmax(0,1fr)_120px_84px] items-center gap-3 px-3.5 py-3 text-sm ${i ? "border-t border-zinc-800" : ""}`}>
                  <span className="font-mono text-zinc-500">{sq.index}.</span>
                  <span className="text-pretty">{sq.text}</span>
                  <span className="flex gap-1">
                    {Array.from({ length: TARGET }, (_, k) => (
                      <span key={k} className={`h-2 flex-1 rounded-sm ${k < ok ? "bg-emerald-400" : k < ok + waiting ? "bg-amber-400/60" : "bg-zinc-800"}`} />
                    ))}
                  </span>
                  <span className={`text-right text-xs ${ok >= TARGET ? "text-emerald-300" : ok ? "text-sky-300" : "text-zinc-500"}`}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-2.5">
          <span className="text-[17px] font-semibold">Panel</span>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(86px,1fr))] overflow-hidden rounded-lg border border-zinc-800">
            {BOARD.map(([key, label, fg]) => (
              <div key={key} className="flex flex-col gap-0.5 border-r border-line p-2.5">
                <span className={`font-mono text-lg font-medium ${counts[key] ? fg : "text-zinc-600"}`}>{counts[key] ?? 0}</span>
                <span className="text-[11px] text-zinc-500">{label}</span>
              </div>
            ))}
          </div>
          <span className="text-xs text-zinc-500">“answers in” counts answers to single sub-questions.</span>
        </div>

        <div className="flex flex-col gap-2.5">
          <div className="flex items-baseline gap-2.5">
            <span className="text-[17px] font-semibold">Responses</span>
            <span className="text-xs text-zinc-500">Anonymised · screened before you see them</span>
          </div>
          {screened && <ScreenCounts coverage={screened.coverage} />}
          {!screened || screened.responses.length === 0 ? (
            <span className="text-sm text-zinc-500">
              {received ? "No accepted answers yet. Held answers wait for a team member; rejected ones are never shown." : "No responses yet."}
            </span>
          ) : (
            screened.responses.map((r) => (
              <div key={r.response_id} className="flex flex-col gap-2 rounded-lg border border-zinc-800 p-3.5">
                <div className="flex flex-wrap items-center gap-2 text-[13px]">
                  <span className="rounded bg-zinc-800 px-1.5 py-px font-mono text-xs font-semibold">{r.ref}</span>
                  <span className="font-medium">{[r.role, r.company].filter(Boolean).join(" · ") || "Former employee"}</span>
                  <span className="ml-auto text-[11px] text-zinc-500">
                    sub-question {r.subquestion_index} · {r.mode}{r.confidence ? ` · confidence ${r.confidence}` : ""}
                  </span>
                  <Pill tone={VERDICT_TONE[r.verdict]}>{r.verdict}</Pill>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-pretty text-zinc-300">{r.text}</p>
                <span className="text-[11px] text-zinc-500 font-mono">{r.response_id}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <EventStream events={events} />
    </div>
  );
}

function ScreenCounts({ coverage }: { coverage: CustomerResponses["coverage"] }) {
  const total = { accepted: 0, redacted: 0, held: 0, rejected: 0, pending: 0 };
  for (const c of Object.values(coverage)) for (const k of Object.keys(total) as (keyof typeof total)[]) total[k] += c[k];
  const parts = (Object.entries(total) as [keyof typeof total, number][]).filter(([, n]) => n);
  if (!parts.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {parts.map(([k, n]) => <Pill key={k} tone={VERDICT_TONE[k]}>{n} {k === "pending" ? "being screened" : k}</Pill>)}
    </div>
  );
}

const EVENT_COLOR: [RegExp, string][] = [
  [/^stage\.failed|^mail\.(blocked|failed)/, "text-red-300"],
  [/^stage\./, "text-sky-300"],
  [/^case\.|^plan\./, "text-emerald-300"],
  [/^approval\.|^mail\./, "text-amber-300"],
  [/^response\./, "text-violet-300"],
];

function eventDetail(e: SynexEvent): string {
  switch (e.type) {
    case "case.created": return String(e.question ?? "");
    case "case.state": return `${e.state}${e.reason ? ` · ${e.reason}` : ""}`;
    case "stage.started": case "stage.done": return String(e.stage);
    case "stage.failed": return `${e.stage} · ${e.error}`;
    case "crustdata.call": return `${e.endpoint} · ${e.credits} credits${e.cache_hit ? " · cache" : ""}`;
    case "llm.call": return `${e.purpose} · ${e.model} · $${Number(e.cost_usd).toFixed(4)}${e.valid ? "" : " · invalid, retried"}`;
    case "plan.approved": return `panel ${e.panel_size} · quoted ₹${Number(e.quoted_price_inr).toLocaleString("en-IN")} · no payment taken`;
    case "outreach.batch_approved": return `${e.sent} sent · ${e.dropped} dropped · by ${e.by}`;
    case "approval.requested": return `${e.ref ?? ""} · sub-questions ${(e.subquestion_indices as number[] | undefined)?.join(", ") ?? ""}`;
    case "approval.approved": case "approval.rejected": return `draft ${e.outreach_id} · by ${e.by}`;
    case "mail.sent": return `draft ${e.outreach_id}`;
    case "mail.blocked": return `draft ${e.outreach_id} · ${e.reason}`;
    case "response.received": return `${e.response_id} · sub-question ${e.subquestion_index} · ${e.kind}`;
    case "response.screened": return `${e.response_id} · ${e.verdict}${e.by && e.by !== "screen" ? ` · by ${e.by}` : ""}`;
    case "job.paused": return String(e.reason ?? "");
    default:
      return "";
  }
}

function EventStream({ events }: { events: SynexEvent[] }) {
  return (
    <div className="flex flex-col rounded-[10px] border border-zinc-800">
      <div className="flex items-center gap-2.5 border-b border-zinc-800 px-4 py-3">
        <span className="text-[15px] font-semibold">Event stream</span>
        <span className="text-xs text-zinc-500">{events.length} events</span>
      </div>
      <div className="flex max-h-[520px] flex-col gap-1.5 overflow-auto px-4 pt-2.5 pb-3.5 font-mono text-xs leading-normal text-zinc-400">
        {[...events].reverse().map((e) => (
          <div key={e.id} className="grid grid-cols-[62px_150px_minmax(0,1fr)] gap-2.5">
            <span className="text-zinc-600">{new Date(e.at).toLocaleTimeString([], { hour12: false })}</span>
            <span className={EVENT_COLOR.find(([re]) => re.test(e.type))?.[1] ?? "text-zinc-400"}>{e.type}</span>
            <span className="break-words">{eventDetail(e)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Result tab -------------------------------------------------------------------------------
// The finished work: per sub-question, the screened answers, how many independent sources back them, the
// confidence computed in code, and an optional summary whose every sentence cites an answer.

const CONF_TONE: Record<string, "emerald" | "amber" | "zinc"> = { High: "emerald", Medium: "amber", Low: "zinc" };

function ResultTab({ caseId, events }: { caseId: string; events: SynexEvent[] }) {
  const [result, setResult] = useState<CaseResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const screened = events.filter((e) => e.type === "response.screened" || e.type === "result.summary_written").length;

  useEffect(() => {
    api.result(caseId).then(setResult).catch((e) => setError(e.message));
  }, [caseId, screened]);

  async function summarise() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.writeSummary(caseId));
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg.startsWith("503")
        ? "The summary could not be written (model unavailable or budget reached). The structured result below is still valid."
        : msg.startsWith("409") ? "There is no accepted answer to summarise yet." : msg);
    } finally {
      setBusy(false);
    }
  }

  async function close() {
    if (!window.confirm("Close this case? Expert links will stop taking answers and the result becomes final.")) return;
    setBusy(true);
    setError(null);
    try {
      await api.closeCase(caseId);
      setResult(await api.result(caseId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!result) return <p className="text-sm text-zinc-500">{error ?? "Loading result…"}</p>;
  const answered = result.subquestions.filter((s) => s.status === "answered").length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 rounded-[10px] border border-zinc-800 bg-panel px-4 py-3 text-[13px]">
        <span className="text-[15px] font-semibold">Result</span>
        <span className="text-zinc-400">{answered} of {result.subquestions.length} sub-questions answered</span>
        <span className="text-xs text-zinc-500">
          Confidence and sources are computed in code from screened answers: High needs 3 independent sources, Medium 2, Low 1.
        </span>
        <button
          onClick={summarise}
          disabled={busy || answered === 0 || result.summary_status === "written"}
          className="ml-auto rounded-md bg-foreground px-3 py-2 text-sm font-medium text-background disabled:opacity-40"
        >
          {busy ? "Writing…" : result.summary_status === "written" ? "Summary written" : result.summary_status === "stale" ? "Update summary" : "Write summary"}
        </button>
        {result.state === "COLLECTING" && (
          <button
            onClick={close}
            disabled={busy || answered === 0}
            className="rounded-md border border-zinc-700 px-3 py-2 text-sm disabled:opacity-40"
            title={answered === 0 ? "Needs at least one accepted answer" : "Stop collecting and deliver this result"}
          >
            Close case
          </button>
        )}
      </div>
      {result.state === "DELIVERED" && (
        <p className="rounded-lg border border-emerald-900 bg-[#07110d] px-4 py-3 text-[13px] text-emerald-300">
          Delivered. Collection is closed: expert links no longer take answers, and this result is final.
        </p>
      )}
      {error && <span className="text-[13px] text-red-300">{error}</span>}
      {result.subquestions.map((sq) => <ResultCard key={sq.index} sq={sq} />)}
    </div>
  );
}

function ResultCard({ sq }: { sq: ResultSubQuestion }) {
  return (
    <div className="flex flex-col gap-2.5 rounded-lg border border-zinc-800 px-4 py-3.5 text-[13px]">
      <div className="flex gap-2.5">
        <span className="font-mono text-sm text-zinc-500">{sq.index}.</span>
        <span className="flex-1 text-[15px] font-medium text-pretty">{sq.text}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {sq.status === "answered" ? (
          <>
            {sq.confidence && <Pill tone={CONF_TONE[sq.confidence]}>confidence {sq.confidence}</Pill>}
            <Pill tone="zinc">{sq.independent_sources} independent source{sq.independent_sources === 1 ? "" : "s"}</Pill>
            {sq.label && <Pill tone="zinc">{sq.label}</Pill>}
          </>
        ) : (
          sq.status === "not sourced"
            ? <Pill tone="zinc">not sourced in development mode</Pill>
            : <Pill tone="amber">cannot verify yet: no accepted answer</Pill>
        )}
        <span className="text-zinc-500">
          {sq.coverage.received} received · {sq.coverage.accepted} accepted · {sq.coverage.redacted} redacted · {sq.coverage.held} held · {sq.coverage.rejected} rejected
        </span>
      </div>
      {sq.summary && (
        <div className="flex flex-col gap-1 rounded-md bg-hover px-3 py-2.5">
          {sq.summary.sentences.map((s, i) => (
            <span key={i} className="leading-relaxed text-zinc-200">
              {s.text.replace(/\s*\[[A-Za-z0-9]+\]/g, "")} {s.cites.map((c) => <span key={c} className="font-mono text-xs text-sky-300">[{c}]</span>)}
            </span>
          ))}
          {sq.summary.dropped_uncited > 0 && (
            <span className="text-xs text-zinc-500">{sq.summary.dropped_uncited} uncited sentence(s) dropped by the checker</span>
          )}
        </div>
      )}
      {sq.answers.map((a) => (
        <div key={a.response_id} className="flex flex-col gap-1 border-l-2 border-zinc-800 pl-3">
          <span className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
            <span className="font-mono text-zinc-300">{a.ref}</span>
            {[a.role, a.company].filter(Boolean).join(" · ")}
            <Pill tone={a.verdict === "accepted" ? "emerald" : "amber"}>{a.verdict}</Pill>
            {a.confidence && <span>self-rated {a.confidence}</span>}
            <span className="font-mono">{a.response_id}</span>
          </span>
          <span className="leading-relaxed whitespace-pre-wrap text-zinc-300">{a.text}</span>
        </div>
      ))}
      {sq.groups.filter((g) => g.refs.length > 1).map((g, i) => (
        <span key={i} className="text-xs text-zinc-500">Counted as one source: {g.refs.join(", ")} ({g.evidence})</span>
      ))}
      {sq.independence_unchecked.length > 0 && (
        <span className="text-xs text-zinc-500">
          Independence not fully checked for {sq.independence_unchecked.map((u) => `${u.ref} (missing ${u.missing.join(", ")})`).join("; ")}
        </span>
      )}
    </div>
  );
}

// ---- Costs tab --------------------------------------------------------------------------------

function CostsTab({ data }: { data: CustomerCase }) {
  const [costs, setCosts] = useState<CaseCosts | null>(null);
  useEffect(() => {
    api.caseCosts(data.id).then(setCosts).catch(() => setCosts(null));
  }, [data.id, data.cost.model_usd, data.cost.crustdata_credits]);

  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-[17px] font-semibold">Cost log</span>
      <p className="text-xs text-zinc-500">Every Crustdata and model call of this case with what it cost. No payment is taken.</p>
      <CostTable costs={costs} />
    </div>
  );
}
