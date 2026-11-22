import type { CaseCosts } from "@/lib/api";

// Every model and Crustdata call with its cost, oldest first. Holds call ids, purposes and costs only.
export function CostTable({ costs, showCase = false }: { costs: CaseCosts | null; showCase?: boolean }) {
  if (!costs) return <span className="text-sm text-zinc-500">Loading…</span>;
  const rows = [
    ...costs.llm_calls.map((c) => ({
      at: c.created_at, id: c.call_id, case: c.case_id, purpose: c.purpose, model: c.model,
      units: `${c.input_tokens ?? 0} → ${c.output_tokens ?? 0} tok${c.valid ? "" : " · invalid"}`, usd: `$${(c.cost_usd ?? 0).toFixed(4)}`,
    })),
    ...costs.crustdata_calls.map((c) => ({
      at: c.created_at, id: c.call_id, case: c.case_id, purpose: c.purpose, model: c.endpoint,
      units: `${c.credits} credits${c.cache_hit ? " · cache" : ""}${c.error ? " · error" : ""}`, usd: "—",
    })),
  ].sort((a, b) => a.at.localeCompare(b.at));
  if (!rows.length) return <span className="text-sm text-zinc-500">No calls yet.</span>;
  const cols = showCase ? "grid-cols-[90px_100px_minmax(0,1fr)_200px_150px_80px]" : "grid-cols-[minmax(0,1fr)_200px_150px_80px]";
  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 text-[13px]">
      <div className={`grid ${cols} gap-3 bg-hover px-3.5 py-2 text-[11px] uppercase tracking-[.05em] text-zinc-500`}>
        {showCase && <><span>Call</span><span>Case</span></>}
        <span>Purpose</span><span>Model / endpoint</span><span>Tokens / credits</span><span className="text-right">USD</span>
      </div>
      {rows.map((r) => (
        <div key={r.id} className={`grid ${cols} gap-3 border-t border-line px-3.5 py-2 font-mono text-xs`}>
          {showCase && <><span className="truncate text-zinc-500">{r.id.slice(0, 8)}</span><span className="text-zinc-500">{r.case ?? "—"}</span></>}
          <span className="truncate">{r.purpose}</span>
          <span className="truncate text-zinc-400">{r.model}</span>
          <span>{r.units}</span>
          <span className="text-right">{r.usd}</span>
        </div>
      ))}
      <div className={`grid ${cols} gap-3 border-t border-zinc-800 px-3.5 py-2 font-mono text-xs text-zinc-300`}>
        {showCase && <><span /><span /></>}
        <span>Total</span><span /><span>{costs.totals.crustdata_credits} credits</span>
        <span className="text-right">${costs.totals.model_usd.toFixed(4)}</span>
      </div>
    </div>
  );
}
