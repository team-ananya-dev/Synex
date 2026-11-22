"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Approval, type Approver, type OutreachStatus } from "@/lib/api";
import { Pill } from "@/components/StateBadge";

// Operator-only: shows real names from Crustdata. Never link this from a customer screen.
const STATUS_TONE: Record<OutreachStatus, "amber" | "emerald" | "zinc" | "red"> = {
  DRAFTED: "amber",
  SENT: "emerald",
  REJECTED: "zinc",
  BLOCKED: "red",
  FAILED: "red",
};

export default function ApprovalsPage() {
  const [items, setItems] = useState<Approval[] | null>(null);
  const [approver, setApprover] = useState<Approver>("ananya");
  const [onlyDrafted, setOnlyDrafted] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(() => {
    api.listApprovals(onlyDrafted ? { status: "DRAFTED" } : {})
      .then((rows) => { setItems(rows); setError(null); })
      .catch((e) => setError(e.message));
  }, [onlyDrafted]);

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  async function decide(id: number, decision: "approve" | "reject") {
    setBusy(id);
    setError(null);
    try {
      await api.decide(id, decision, approver);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-[26px] font-semibold tracking-[-.02em]">Approval queue</h1>
        <p className="text-sm leading-normal text-zinc-400">
          Nothing is sent without a click here. Mail goes only to the teammate allowlist; any other address is blocked
          and logged.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-[13px]">
        <label className="flex items-center gap-2">
          Approving as
          <select
            value={approver}
            onChange={(e) => setApprover(e.target.value as Approver)}
            className="rounded border border-zinc-700 bg-background px-2 py-1"
          >
            <option value="ananya">ananya</option>
            <option value="dev">dev</option>
          </select>
        </label>
        <button onClick={() => setOnlyDrafted((v) => !v)} className="flex items-center gap-1.5 text-zinc-400">
          <span className={`flex h-3.5 w-3.5 items-center justify-center rounded-[3px] border text-[10px] text-background ${onlyDrafted ? "border-foreground bg-foreground" : "border-zinc-600"}`}>
            {onlyDrafted && "✓"}
          </span>
          Waiting only
        </button>
        {error && <span className="text-red-300">{error}</span>}
      </div>

      {items === null ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">Nothing waiting.</p>
      ) : (
        <div className="flex flex-col gap-3.5">
          {items.map((a) => (
            <div key={a.id} className="flex flex-col gap-3 rounded-lg border border-zinc-800 p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone={STATUS_TONE[a.status]}>{a.status}</Pill>
                <span className="font-medium">{a.name}</span>
                <span className="text-zinc-500">
                  {[a.persona_title, a.persona_company, a.tenure_months != null && `${a.tenure_months} months`].filter(Boolean).join(" · ")}
                </span>
                <span className="ml-auto text-xs text-zinc-500">
                  case {a.case_id} · sub-questions {a.subquestion_indices.join(", ")}
                </span>
              </div>

              {a.flags.length > 0 && (
                <div className="flex flex-col gap-0.5 rounded-md border border-[#4a3510] bg-[#120c04] px-2.5 py-2 text-xs text-amber-300">
                  {a.flags.map((f, i) => <span key={i}>⚑ {f.rule}: {f.reason}</span>)}
                </div>
              )}

              <div className="flex flex-col gap-1.5 rounded-md bg-hover p-3.5">
                <div className="text-xs text-zinc-500">
                  To: <span className="font-mono text-zinc-300">{a.to_address}</span> (teammate playing this expert)
                </div>
                <span className="font-medium">{a.subject}</span>
                <pre className="mt-1 whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-zinc-300">{a.body}</pre>
              </div>

              {a.block_reason && <p className="text-[13px] text-red-300">Blocked: {a.block_reason}</p>}
              {a.decided_by && (
                <p className="text-xs text-zinc-500">
                  {a.status.toLowerCase()} by {a.decided_by} at {a.decided_at && new Date(a.decided_at).toLocaleString()}
                </p>
              )}

              {a.status === "DRAFTED" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => decide(a.id, "approve")}
                    disabled={busy === a.id}
                    className="rounded-md bg-emerald-600 px-3.5 py-[7px] font-medium text-white disabled:opacity-40"
                  >
                    Approve and send
                  </button>
                  <button
                    onClick={() => decide(a.id, "reject")}
                    disabled={busy === a.id}
                    className="rounded-md border border-zinc-700 px-3.5 py-[7px] disabled:opacity-40"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
