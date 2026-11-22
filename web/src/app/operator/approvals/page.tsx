"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Approval, type Approver, type OutreachStatus } from "@/lib/api";

// Operator-only: shows real names from Crustdata. Never link this from a customer screen.
const STATUS_STYLE: Record<OutreachStatus, string> = {
  DRAFTED: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  SENT: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  REJECTED: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  BLOCKED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
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
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Approval queue</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Nothing is sent without a click here. Mail goes only to the teammate allowlist; any other address is
          blocked and logged.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2">
          Approving as
          <select
            value={approver}
            onChange={(e) => setApprover(e.target.value as Approver)}
            className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
          >
            <option value="ananya">ananya</option>
            <option value="dev">dev</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={onlyDrafted} onChange={(e) => setOnlyDrafted(e.target.checked)} />
          Waiting only
        </label>
        {error && <span className="text-red-600">{error}</span>}
      </div>

      {items === null ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">Nothing waiting.</p>
      ) : (
        <ul className="space-y-4">
          {items.map((a) => (
            <li key={a.id} className="space-y-3 rounded-md border border-zinc-200 p-4 text-sm dark:border-zinc-800">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[a.status]}`}>{a.status}</span>
                <span className="font-medium">{a.name}</span>
                <span className="text-zinc-500">
                  {a.persona_title} · {a.persona_company}
                  {a.tenure_months != null && ` · ${a.tenure_months} months`}
                </span>
                <span className="ml-auto text-xs text-zinc-500">
                  case {a.case_id} · sub-questions {a.subquestion_indices.join(", ")}
                </span>
              </div>

              {a.flags.length > 0 && (
                <ul className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
                  {a.flags.map((f, i) => <li key={i}>⚑ {f.rule}: {f.reason}</li>)}
                </ul>
              )}

              <div className="rounded bg-zinc-50 p-3 dark:bg-zinc-900">
                <div className="text-xs text-zinc-500">To: {a.to_address} (teammate playing this expert)</div>
                <div className="font-medium">{a.subject}</div>
                <pre className="mt-2 whitespace-pre-wrap font-sans text-zinc-700 dark:text-zinc-300">{a.body}</pre>
              </div>

              {a.block_reason && <p className="text-red-600">Blocked: {a.block_reason}</p>}
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
                    className="rounded-md bg-emerald-600 px-3 py-1.5 font-medium text-white disabled:opacity-40"
                  >
                    Approve and send
                  </button>
                  <button
                    onClick={() => decide(a.id, "reject")}
                    disabled={busy === a.id}
                    className="rounded-md border border-zinc-300 px-3 py-1.5 dark:border-zinc-700"
                  >
                    Reject
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
