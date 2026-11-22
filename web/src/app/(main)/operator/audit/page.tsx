"use client";

// Operator screen: the hash-chained audit trail and the cost log. Payloads can hold real people's
// details (stage results), so this page is operator-only, like /cases/{id} and /approvals.
import { useCallback, useEffect, useState } from "react";
import { api, type AuditEvent, type CaseCosts, type CaseSummary, type ChainCheck, type TotalCosts } from "@/lib/api";
import { CostTable } from "@/components/CostTable";

const FILTERS: [string, string, (t: string) => boolean][] = [
  ["all", "All", () => true],
  ["case", "Case and stages", (t) => /^(case|stage|plan|job)\./.test(t)],
  ["calls", "Model and Crustdata calls", (t) => /^(llm|crustdata)\./.test(t)],
  ["actions", "Approvals and mail", (t) => /^(approval|mail)\./.test(t)],
  ["responses", "Responses", (t) => t.startsWith("response.")],
];

const COLOR: [RegExp, string][] = [
  [/failed|blocked/, "text-red-300"],
  [/^stage\./, "text-sky-300"],
  [/^(case|plan)\./, "text-emerald-300"],
  [/^(approval|mail|ledger)\./, "text-amber-300"],
  [/^response\./, "text-violet-300"],
];

function detail(e: AuditEvent): string {
  const p = e.payload;
  if (e.type === "stage.done") return `${p.stage} · result recorded`;
  const text = Object.entries(p).map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join(" ");
  return text.length > 180 ? `${text.slice(0, 180)}…` : text;
}

async function loadAll(caseId: string): Promise<AuditEvent[]> {
  const out: AuditEvent[] = [];
  for (let after = 0; ; ) {
    const page = await api.auditEvents({ case_id: caseId === "all" ? undefined : caseId, after, limit: 1000 });
    out.push(...page);
    if (page.length < 1000) return out;
    after = page[page.length - 1].id;
  }
}

export default function AuditPage() {
  const [caseId, setCaseId] = useState("all");
  const [filter, setFilter] = useState("all");
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [rows, setRows] = useState<AuditEvent[] | null>(null);
  const [check, setCheck] = useState<ChainCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [totals, setTotals] = useState<TotalCosts | null>(null);
  const [caseCosts, setCaseCosts] = useState<CaseCosts | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    loadAll(caseId).then((r) => { setRows(r); setError(null); }).catch((e) => setError(e.message));
    api.totalCosts().then(setTotals).catch(() => {});
    if (caseId !== "all") api.caseCosts(caseId).then(setCaseCosts).catch(() => setCaseCosts(null));
  }, [caseId]);

  useEffect(() => {
    api.listCustomerCases().then(setCases).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function verify() {
    setChecking(true);
    try {
      setCheck(await api.verifyChain());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(rows ?? [], null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `synex-audit-${caseId}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const match = FILTERS.find(([k]) => k === filter)![2];
  const shown = (rows ?? []).filter((e) => match(e.type)).reverse();
  const verifyStyle = !check
    ? "border-zinc-800 text-zinc-400"
    : check.ok ? "border-[#1f3a2f] bg-[#07110d] text-emerald-300" : "border-red-900 bg-[#1c0606] text-red-300";

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end gap-3.5">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-[26px] font-semibold tracking-[-.02em]">Audit trail</h1>
          <span className="text-sm text-zinc-400">
            {rows?.length ?? "…"} events · append-only, each event stores the previous event&apos;s hash
          </span>
        </div>
        <span className={`ml-auto rounded-md border px-3 py-1.5 text-[13px] ${verifyStyle}`}>
          {!check ? "Chain not checked yet"
            : check.ok ? `✓ Chain intact · ${check.events_checked} events recomputed`
            : `✗ Chain broken at event ${check.first_bad_event_id}`}
        </span>
        <button onClick={verify} disabled={checking} className="rounded-md border border-zinc-700 px-3 py-1.5 text-[13px] disabled:opacity-40">
          {checking ? "Checking…" : "Verify chain"}
        </button>
        <button onClick={exportJson} disabled={!rows} className="rounded-md border border-zinc-700 px-3 py-1.5 text-[13px] disabled:opacity-40">
          Export JSON
        </button>
        <button onClick={load} className="rounded-md border border-zinc-700 px-3 py-1.5 text-[13px]">Refresh</button>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 text-[13px]">
        <span className="text-zinc-400">Case</span>
        <select
          value={caseId}
          onChange={(e) => setCaseId(e.target.value)}
          className="max-w-[420px] rounded border border-zinc-700 bg-background px-2 py-1"
        >
          <option value="all">All cases</option>
          {cases.map((c) => <option key={c.id} value={c.id}>{c.id} · {c.question.slice(0, 60)}</option>)}
        </select>
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`rounded border border-zinc-800 px-2.5 py-0.5 text-xs ${filter === key ? "bg-foreground text-background" : "text-zinc-400 hover:text-foreground"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {error && <p className="text-[13px] text-red-300">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-zinc-800 text-[13px]">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-[50px_80px_100px_170px_minmax(0,1fr)_180px] gap-3 bg-hover px-3.5 py-2 text-[11px] uppercase tracking-[.05em] text-zinc-500">
            <span>#</span><span>Time</span><span>Case</span><span>Event</span><span>Detail</span><span>prev → hash</span>
          </div>
          {rows === null ? (
            <p className="px-3.5 py-3 text-zinc-500">Loading…</p>
          ) : shown.length === 0 ? (
            <p className="px-3.5 py-3 text-zinc-500">No events.</p>
          ) : (
            shown.map((e) => (
              <div key={e.id} className={`grid grid-cols-[50px_80px_100px_170px_minmax(0,1fr)_180px] items-start gap-3 border-t border-line px-3.5 py-2 ${check && !check.ok && e.id === check.first_bad_event_id ? "bg-[#1c0606]" : ""}`}>
                <span className="font-mono text-zinc-500">{e.id}</span>
                <span className="font-mono text-xs text-zinc-400">{new Date(e.at).toLocaleTimeString([], { hour12: false })}</span>
                <span className="truncate font-mono text-xs text-zinc-500">{e.case_id ?? "—"}</span>
                <span className={`font-mono text-xs ${COLOR.find(([re]) => re.test(e.type))?.[1] ?? "text-zinc-400"}`}>{e.type}</span>
                <span className="break-words text-xs text-zinc-300">{detail(e)}</span>
                <span className="font-mono text-[11px] text-zinc-500">{e.prev_hash.slice(0, 8)} → {e.hash.slice(0, 8)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2.5">
        <div className="flex flex-wrap items-baseline gap-2.5">
          <span className="text-[17px] font-semibold">Cost log</span>
          {totals && (
            <span className="text-xs text-zinc-500">
              All cases: {totals.crustdata_credits} Crustdata credits ({totals.crustdata_calls} calls) · ${totals.model_usd.toFixed(4)} model
              spend ({totals.llm_calls} calls) · ${totals.model_remaining_usd.toFixed(2)} of ${totals.model_budget_usd} budget left
              {totals.demo_mode ? " · demo mode" : " · dev mode"}
            </span>
          )}
        </div>
        {caseId === "all"
          ? <span className="text-sm text-zinc-500">Pick a case to see each call.</span>
          : <CostTable costs={caseCosts} showCase />}
      </div>
    </div>
  );
}
