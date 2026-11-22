"use client";

// Customer screen. Uses only /customer routes (never a name, headline, profile link, city or email)
// plus the per-case cost log, which holds call ids, purposes and costs only.
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  api, type CaseCosts, type CustomerCase, type ExpertCard, type OutreachStatus, type SubQuestion, type SynexEvent,
} from "@/lib/api";
import { useCaseEvents } from "@/lib/useCaseEvents";
import { Pill, SimulatedTag, StateBadge, TONE } from "@/components/StateBadge";
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
  "ledger.hold", "ledger.capture", "ledger.release", "response.received",
]);

type Tab = "plan" | "live" | "ledger";
type SourcingSummary = Record<string, {
  companies: { asked: string; resolved: boolean; name: string | null; total_matches: number | null }[];
  found: number;
}>;

const money = (n: number) => `$${n.toFixed(2)}`;
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
  const done = new Set(events.filter((e) => e.type === "stage.done").map((e) => e.stage as string));
  const started = new Set(events.filter((e) => e.type === "stage.started").map((e) => e.stage as string));
  const failed = events.find((e) => e.type === "stage.failed");
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
        {failed && <Alert>Stage {String(failed.stage)} failed: {String(failed.error)}</Alert>}
      </section>

      <section className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3">
        <Counter label="Crustdata credits" value={`${data.cost.crustdata_credits.toFixed(1)} / ${data.cost.credit_cap}`} />
        <Counter label="Model spend" value={`$${data.cost.model_usd.toFixed(4)}`} />
        <Counter label="Held · simulated" value={money(data.ledger.balance.remaining)} amber />
        <Counter label="Charged · simulated" value={money(data.ledger.balance.captured)} amber />
      </section>

      <section className="flex flex-wrap gap-1.5 text-xs">
        {STAGES.map(([key, label]) => {
          const s = failed?.stage === key ? "failed" : done.has(key) ? "done" : started.has(key) ? "running" : "waiting";
          return <span key={key} className={`rounded px-2 py-1 ${STAGE_STYLE[s]}`}>{label} · {s}</span>;
        })}
      </section>

      <div className="flex gap-1 border-b border-zinc-800">
        {(["plan", "live", "ledger"] as Tab[]).map((t) => (
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
      {current === "ledger" && <LedgerTab data={data} />}
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
    <div className="flex flex-col gap-3.5 rounded-[10px] border border-zinc-800 bg-panel p-[18px]">
      <div className="flex items-center gap-2">
        <span className="text-[15px] font-semibold">Approve and hold</span>
        <span className="ml-auto"><SimulatedTag /></span>
      </div>
      <div className="flex flex-col gap-2 text-[13px]">
        <Row label="Sub-questions" value={String(quote.subquestions)} />
        <Row label="Per answered sub-question" value={money(quote.price_per_subquestion)} />
        <div className="h-px bg-zinc-800" />
        <div className="flex justify-between text-[15px]">
          <span>Maximum hold</span>
          <span className="font-mono font-medium">{money(quote.hold_amount)}</span>
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
      <label className="flex flex-col gap-1.5 text-[13px]">
        <span className="text-zinc-400">Budget cap (USD, simulated)</span>
        <input
          type="number"
          min={quote.hold_amount}
          step="any"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          className="rounded-md border border-zinc-700 bg-background px-2.5 py-2 font-mono text-sm outline-none focus:border-zinc-500"
        />
      </label>
      <p className="text-xs leading-relaxed text-zinc-400">
        You are charged only for sub-questions that get answered; the rest of the hold is released when the case closes.
        No money moves: this is a simulated ledger.
      </p>
      {error && <span className="text-[13px] text-red-300">{error}</span>}
      <button
        onClick={approve}
        disabled={busy || !(Number(budget) > 0)}
        className="rounded-md bg-foreground px-3.5 py-2.5 text-sm font-medium text-background disabled:opacity-40"
      >
        {busy ? "Approving…" : `Approve plan · hold ${money(quote.hold_amount)}`}
      </button>
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
  ["ANSWERED", "answered", "text-violet-300"],
  ["REJECTED", "rejected", "text-zinc-400"],
  ["BLOCKED", "blocked", "text-red-300"],
  ["FAILED", "send failed", "text-red-300"],
];

const KIND_LABEL: Record<string, string> = { answer: "answer", dont_know: "doesn't know", confidential: "declined: confidential" };

function LiveTab({ data, events }: { data: CustomerCase; events: SynexEvent[] }) {
  const responses = events.filter((e) => e.type === "response.received");
  const counts: Record<string, number> = { ...data.outreach, ANSWERED: responses.length };

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-6">
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
          <span className="text-xs text-zinc-500">“answered” counts answers to single sub-questions.</span>
        </div>

        <div className="flex flex-col gap-2.5">
          <div className="flex items-baseline gap-2.5">
            <span className="text-[17px] font-semibold">Responses</span>
            <span className="text-xs text-zinc-500">Anonymised · answer text is shown only after screening</span>
          </div>
          {responses.length === 0 ? (
            <span className="text-sm text-zinc-500">No responses yet.</span>
          ) : (
            <div className="flex flex-col overflow-hidden rounded-lg border border-zinc-800">
              {responses.map((r, i) => (
                <div key={r.id} className={`flex flex-wrap items-center gap-2 px-3.5 py-2.5 text-[13px] ${i ? "border-t border-line" : ""}`}>
                  <span className="rounded bg-zinc-800 px-1.5 py-px font-mono text-xs font-semibold">{String(r.response_id)}</span>
                  <span>Sub-question {String(r.subquestion_index)}</span>
                  <span className="text-zinc-500">{KIND_LABEL[String(r.kind)] ?? String(r.kind)} · {String(r.mode)}</span>
                  <span className="ml-auto text-[11px] text-zinc-500">{new Date(r.at).toLocaleTimeString()}</span>
                  <Pill tone="zinc">awaiting screen</Pill>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <EventStream events={events} />
    </div>
  );
}

const EVENT_COLOR: [RegExp, string][] = [
  [/^stage\.failed|^mail\.(blocked|failed)/, "text-red-300"],
  [/^stage\./, "text-sky-300"],
  [/^case\.|^plan\./, "text-emerald-300"],
  [/^approval\.|^mail\./, "text-amber-300"],
  [/^response\./, "text-violet-300"],
  [/^ledger\./, "text-amber-300"],
];

function eventDetail(e: SynexEvent): string {
  switch (e.type) {
    case "case.created": return String(e.question ?? "");
    case "case.state": return `${e.state}${e.reason ? ` · ${e.reason}` : ""}`;
    case "stage.started": case "stage.done": return String(e.stage);
    case "stage.failed": return `${e.stage} · ${e.error}`;
    case "crustdata.call": return `${e.endpoint} · ${e.credits} credits${e.cache_hit ? " · cache" : ""}`;
    case "llm.call": return `${e.purpose} · ${e.model} · $${Number(e.cost_usd).toFixed(4)}${e.valid ? "" : " · invalid, retried"}`;
    case "plan.approved": return `panel ${e.panel_size} · hold $${e.hold} (simulated)`;
    case "approval.requested": return `${e.ref ?? ""} · sub-questions ${(e.subquestion_indices as number[] | undefined)?.join(", ") ?? ""}`;
    case "approval.approved": case "approval.rejected": return `draft ${e.outreach_id} · by ${e.by}`;
    case "mail.sent": return `draft ${e.outreach_id}`;
    case "mail.blocked": return `draft ${e.outreach_id} · ${e.reason}`;
    case "response.received": return `${e.response_id} · sub-question ${e.subquestion_index} · ${e.kind}`;
    case "job.paused": return String(e.reason ?? "");
    default:
      if (e.type.startsWith("ledger.")) return `$${e.amount} ${e.currency ?? ""}`;
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

// ---- Ledger tab -------------------------------------------------------------------------------

const LEDGER_COLOR: Record<string, string> = { HOLD: "text-amber-300", CAPTURE: "text-emerald-300", RELEASE: "text-zinc-400" };

function LedgerTab({ data }: { data: CustomerCase }) {
  const [costs, setCosts] = useState<CaseCosts | null>(null);
  useEffect(() => {
    api.caseCosts(data.id).then(setCosts).catch(() => setCosts(null));
  }, [data.id, data.cost.model_usd, data.cost.crustdata_credits]);
  const b = data.ledger.balance;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        {([["Held", b.held], ["Captured", b.captured], ["Released", b.released], ["Remaining", b.remaining]] as const).map(([l, v]) => (
          <Counter key={l} label={l} value={money(v)} />
        ))}
      </div>

      <div className="flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[17px] font-semibold">Ledger</span>
          <SimulatedTag>{b.currency}</SimulatedTag>
        </div>
        {data.ledger.entries.length === 0 ? (
          <span className="text-sm text-zinc-500">Nothing held yet.</span>
        ) : (
          <div className="overflow-hidden rounded-lg border border-zinc-800">
            {data.ledger.entries.map((l, i) => (
              <div key={i} className={`grid grid-cols-[90px_90px_minmax(0,1fr)_90px_120px] items-center gap-3 px-3.5 py-[9px] text-[13px] ${i ? "border-t border-zinc-800" : ""}`}>
                <span className={`font-mono ${LEDGER_COLOR[l.kind]}`}>{l.kind}</span>
                <span className="font-mono">{money(l.amount)}</span>
                <span className="text-zinc-400">{l.note}</span>
                <span className="text-zinc-500">{l.created_by}</span>
                <span className="text-right text-zinc-500">{new Date(l.created_at).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2.5">
        <span className="text-[17px] font-semibold">Cost log</span>
        <CostTable costs={costs} />
      </div>
    </div>
  );
}
