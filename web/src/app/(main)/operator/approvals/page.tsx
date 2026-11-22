"use client";

// Operator-only: full answer text of held responses and real names in the invitation log.
// Never link this from a customer screen.
import { useCallback, useEffect, useState } from "react";
import { api, type Approval, type Approver, type OperatorResponse, type OutreachStatus } from "@/lib/api";
import { Pill } from "@/components/StateBadge";

const STATUS_TONE: Record<OutreachStatus, "amber" | "emerald" | "zinc" | "red"> = {
  DRAFTED: "amber",
  SENT: "emerald",
  REJECTED: "zinc",
  BLOCKED: "red",
  FAILED: "red",
};

export default function OperatorQueuePage() {
  const [held, setHeld] = useState<OperatorResponse[] | null>(null);
  const [invites, setInvites] = useState<Approval[] | null>(null);
  const [approver, setApprover] = useState<Approver>("ananya");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    api.operatorResponses({ status: "held" }).then(setHeld).catch((e) => setError(e.message));
    api.listApprovals().then(setInvites).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  async function review(id: string, decision: "accept" | "reject") {
    setBusy(id);
    setError(null);
    try {
      await api.reviewHeld(id, approver, decision);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-[26px] font-semibold tracking-[-.02em]">Operator queue</h1>
        <p className="text-sm leading-normal text-zinc-400">
          Held answers wait here for a team member to accept or reject them; nobody edits an expert&apos;s text. Invitations
          are approved by the customer on the case page; below is the log of what was sent.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-[13px]">
        <label className="flex items-center gap-2">
          Reviewing as
          <select
            value={approver}
            onChange={(e) => setApprover(e.target.value as Approver)}
            className="rounded border border-zinc-700 bg-background px-2 py-1"
          >
            <option value="ananya">ananya</option>
            <option value="dev">dev</option>
          </select>
        </label>
        {error && <span className="text-red-300">{error}</span>}
      </div>

      <section className="flex flex-col gap-3.5">
        <div className="flex items-baseline gap-2.5">
          <h2 className="text-lg font-semibold">Held answers</h2>
          {held && held.length > 0 && <Pill tone="amber">{held.length}</Pill>}
        </div>
        {held === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : held.length === 0 ? (
          <p className="text-sm text-zinc-500">Nothing held.</p>
        ) : (
          held.map((h) => (
            <div key={h.response_id} className="flex flex-col gap-2.5 rounded-lg border border-[#4a3510] p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone="amber">held</Pill>
                <span className="font-mono text-xs">{h.response_id}</span>
                <span className="font-medium">{h.ref}</span>
                <span className="text-zinc-500">{[h.persona_title, h.persona_company].filter(Boolean).join(" · ")}</span>
                <span className="ml-auto text-xs text-zinc-500">case {h.case_id} · sub-question {h.subquestion_index}</span>
              </div>
              <span className="text-[13px] text-amber-300">Screen: {h.reason}</span>
              {h.code_flags.length > 0 && (
                <span className="text-xs text-amber-300/80">Code rule matched: {h.code_flags.map((f) => `“${f}”`).join(", ")}</span>
              )}
              <div className="flex flex-col gap-1 rounded-md bg-hover px-3 py-2.5">
                <span className="text-[11px] text-zinc-500">Answer as submitted{h.confidence ? ` · confidence ${h.confidence}` : ""}</span>
                <span className="leading-relaxed whitespace-pre-wrap text-zinc-300">{h.text}</span>
              </div>
              <span className="text-xs text-zinc-500">Accept shows this answer to the customer as written. Reject excludes it.</span>
              <div className="flex gap-2">
                <button
                  onClick={() => review(h.response_id, "accept")}
                  disabled={busy === h.response_id}
                  className="rounded-md bg-emerald-600 px-3.5 py-[7px] font-medium text-white disabled:opacity-40"
                >
                  Accept answer
                </button>
                <button
                  onClick={() => review(h.response_id, "reject")}
                  disabled={busy === h.response_id}
                  className="rounded-md border border-zinc-700 px-3.5 py-[7px] disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </div>
          ))
        )}
      </section>

      <section className="flex flex-col gap-3.5">
        <h2 className="text-lg font-semibold">Invitation log</h2>
        <p className="text-xs text-zinc-500">
          Read-only. Every invitation goes to a teammate&apos;s inbox through the local Mailpit server, never to a real
          person.
        </p>
        {invites === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : invites.length === 0 ? (
          <p className="text-sm text-zinc-500">No invitations yet.</p>
        ) : (
          invites.map((a) => (
            <details key={a.id} className="rounded-lg border border-zinc-800 text-sm">
              <summary className="flex cursor-pointer flex-wrap items-center gap-2 px-4 py-3">
                <Pill tone={STATUS_TONE[a.status]}>{a.status}</Pill>
                <span className="font-medium">{a.name}</span>
                <span className="text-zinc-500">
                  {[a.persona_title, a.persona_company, a.tenure_months != null && `${a.tenure_months} months`].filter(Boolean).join(" · ")}
                </span>
                <span className="ml-auto text-xs text-zinc-500">
                  case {a.case_id} · sub-questions {a.subquestion_indices.join(", ")}
                </span>
              </summary>
              <div className="flex flex-col gap-2 border-t border-zinc-800 px-4 py-3">
                {a.flags.length > 0 && (
                  <div className="flex flex-col gap-0.5 rounded-md border border-[#4a3510] bg-[#120c04] px-2.5 py-2 text-xs text-amber-300">
                    {a.flags.map((f, i) => <span key={i}>⚑ {f.rule}: {f.reason}</span>)}
                  </div>
                )}
                <div className="text-xs text-zinc-500">
                  To: <span className="font-mono text-zinc-300">{a.to_address}</span> (teammate playing this expert)
                </div>
                <span className="font-medium">{a.subject}</span>
                <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-zinc-300">{a.body}</pre>
                {a.block_reason && <p className="text-[13px] text-red-300">Blocked: {a.block_reason}</p>}
                {a.decided_by && (
                  <p className="text-xs text-zinc-500">
                    {a.status.toLowerCase()} by {a.decided_by}{a.decided_at && ` at ${new Date(a.decided_at).toLocaleString()}`}
                  </p>
                )}
              </div>
            </details>
          ))
        )}
      </section>
    </div>
  );
}
