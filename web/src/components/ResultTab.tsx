"use client";

// The result for a case: per sub-question, the accepted answers, how many independent sources they come from,
// an agreement label and a confidence level, and an optional short cited summary. All figures come from
// GET /customer/cases/{id}/result (computed in code on every read). Customer-safe: refs only, no names or cities.
import { useCallback, useEffect, useState } from "react";
import { api, type CaseResult, type ResultSubquestion, type SynexEvent } from "@/lib/api";
import { Pill } from "@/components/StateBadge";

const CONFIDENCE_TONE = { High: "emerald", Medium: "sky", Low: "amber" } as const;
const LABEL_TONE: Record<string, "emerald" | "amber" | "zinc" | "sky"> = {
  consensus: "emerald", split: "amber", "single source": "zinc", "multiple sources, agreement not assessed": "sky",
};

export function ResultTab({ caseId, events }: { caseId: string; events: SynexEvent[] }) {
  const [result, setResult] = useState<CaseResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  // read again after every screening decision and after a summary is written
  const trigger = events.filter((e) => e.type === "response.screened" || e.type === "result.summary_written").length;
  const load = useCallback(() => {
    api.caseResult(caseId).then((r) => { setResult(r); setError(null); }).catch((e) => setError(e.message));
  }, [caseId]);
  useEffect(load, [load, trigger]);

  async function summarise() {
    setBusy(true);
    setNote(null);
    try {
      setResult(await api.writeSummary(caseId));
    } catch (e) {
      const msg = (e as Error).message;
      setNote(msg.startsWith("503")
        ? "The summary could not be written (model unavailable or budget reached). The structured result below is still valid."
        : msg.startsWith("409") ? "There is no accepted answer to summarise yet." : msg);
    } finally {
      setBusy(false);
    }
  }

  if (error && !result) return <p className="text-sm text-red-300">{error}</p>;
  if (!result) return <p className="text-sm text-zinc-500">Loading…</p>;

  const answered = result.subquestions.filter((s) => s.status === "answered").length;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-800 px-4 py-3 text-sm">
        <span>
          <span className="font-mono">{answered}</span> of <span className="font-mono">{result.subquestions.length}</span> sub-questions have an
          accepted answer
        </span>
        <span className="text-xs text-zinc-500">
          Computed in code from screened answers · {new Date(result.computed_at).toLocaleTimeString()}
        </span>
        <div className="ml-auto flex items-center gap-3">
          {result.summary_status === "stale" && <Pill tone="amber">answers changed since the summary</Pill>}
          <button
            onClick={summarise}
            disabled={busy || answered === 0 || result.summary_status === "written"}
            className="rounded-md bg-foreground px-3.5 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {busy ? "Writing…" : result.summary_status === "written" ? "Summary written" : result.summary_status === "stale" ? "Rewrite summary" : "Write summary"}
          </button>
        </div>
      </div>
      {note && <p className="text-[13px] text-amber-300">{note}</p>}

      {result.subquestions.map((s) => <SubquestionResult key={s.index} s={s} />)}

      <p className="text-xs leading-relaxed text-zinc-500">
        Independence is computed from work history (same company, function and city, with at least 3 months of overlap
        count as one source) and is approximate. Confidence is computed in code: High needs 3 or more independent
        sources, Medium 2, Low 1. The model only writes the summary wording, and a sentence without a valid citation is dropped.
      </p>
    </div>
  );
}

function SubquestionResult({ s }: { s: ResultSubquestion }) {
  const waiting = s.coverage.pending + s.coverage.held;
  return (
    <section className="flex flex-col gap-3.5 rounded-lg border border-zinc-800 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm text-zinc-500">{s.index}.</span>
        <h3 className="min-w-0 flex-1 text-[15px] font-medium text-pretty">{s.text}</h3>
        {s.label && <Pill tone={LABEL_TONE[s.label]}>{s.label}</Pill>}
        {s.confidence && <Pill tone={CONFIDENCE_TONE[s.confidence]}>{s.confidence} confidence</Pill>}
      </div>

      {s.status === "no accepted answer" ? (
        <p className="text-sm text-zinc-400">
          No accepted answer yet.
          {s.coverage.received > 0 && ` ${s.coverage.received} received: ${s.coverage.pending} being screened, ${s.coverage.held} held for a team member, ${s.coverage.rejected} rejected.`}
        </p>
      ) : (
        <>
          <p className="text-xs text-zinc-500">
            {s.independent_sources} independent source{s.independent_sources === 1 ? "" : "s"} from {s.answers.length} accepted answer
            {s.answers.length === 1 ? "" : "s"}
            {waiting > 0 && ` · ${waiting} more waiting to be screened or reviewed`}
          </p>

          {s.summary && (
            <div className="flex flex-col gap-2 rounded-md bg-hover p-3.5">
              <span className="text-[11px] tracking-wide text-zinc-500 uppercase">Summary</span>
              <p className="text-sm leading-relaxed text-zinc-200">
                {s.summary.sentences.map((x, i) => (
                  <span key={i}>
                    {x.text}{" "}
                    <span className="font-mono text-xs text-sky-300">{x.cites.map((c) => `[${c}]`).join("")}</span>{" "}
                  </span>
                ))}
              </p>
              {s.summary.dropped_uncited > 0 && (
                <span className="text-xs text-zinc-500">
                  Cite or drop: {s.summary.dropped_uncited} sentence{s.summary.dropped_uncited === 1 ? "" : "s"} without a valid citation removed.
                </span>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2.5">
            {s.answers.map((a) => (
              <div key={a.response_id} className="flex flex-col gap-1.5 rounded-md border border-line bg-sunken p-3.5">
                <div className="flex flex-wrap items-center gap-2 text-[13px]">
                  <span className="rounded bg-zinc-800 px-1.5 py-px font-mono text-xs font-semibold">{a.ref}</span>
                  <span className="font-medium">{[a.role, a.company].filter(Boolean).join(" · ") || "Former employee"}</span>
                  <span className="ml-auto text-[11px] text-zinc-500">
                    {a.mode}{a.confidence ? ` · self-rated ${a.confidence}` : ""}
                  </span>
                  <Pill tone={a.verdict === "accepted" ? "emerald" : "sky"}>{a.verdict}</Pill>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-zinc-300">{a.text}</p>
              </div>
            ))}
          </div>

          {s.groups.length > 0 && s.answers.length > 1 && (
            <details className="text-xs text-zinc-500">
              <summary className="cursor-pointer">How the sources were counted</summary>
              <ul className="mt-2 flex flex-col gap-1">
                {s.groups.map((g, i) => (
                  <li key={i}>
                    <span className="font-mono">{g.refs.join(" + ")}</span>: {g.refs.length > 1 ? "counted as one source" : "separate source"}
                    {g.evidence ? ` (${g.evidence})` : ""}
                  </li>
                ))}
                {s.independence_unchecked.map((u) => (
                  <li key={u.ref}><span className="font-mono">{u.ref}</span>: counted as separate, missing {u.missing.join(", ")}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
