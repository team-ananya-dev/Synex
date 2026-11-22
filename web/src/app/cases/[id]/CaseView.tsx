"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, type CaseView as Case, type RankedCandidate, type SubQuestion, type SynexEvent } from "@/lib/api";
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

// Events that change what GET /cases/{id} returns; refetch the case when one arrives.
const REFRESH_ON = new Set(["case.state", "stage.done", "stage.failed", "llm.call", "crustdata.call", "job.paused"]);

export function CaseView() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Case | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.getCase(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);
  const onEvent = useCallback((e: SynexEvent) => REFRESH_ON.has(e.type) && load(), [load]);
  const { events, connected } = useCaseEvents(id, onEvent);

  if (error && !data) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-zinc-500">Loading case…</p>;

  const screen = data.stages.s1_question_screen;
  const subs = data.stages.s2_decomposer ?? [];
  const panel = data.stages.s5b_enrich_rerank ?? data.stages.s5_ranker;
  const running = new Set(events.filter((e) => e.type === "stage.started").map((e) => e.stage as string));
  const failed = events.find((e) => e.type === "stage.failed");

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <StateBadge state={data.state} />
          <span className={`text-xs ${connected ? "text-emerald-600" : "text-zinc-500"}`}>
            {connected ? "● live" : "○ not connected"}
          </span>
          <span className="ml-auto text-xs text-zinc-500">case {data.id}</span>
        </div>
        <h1 className="text-xl font-semibold">{data.question}</h1>
        {screen?.verdict === "rewrite" && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            Rewritten for compliance: “{screen.effective_question}” ({screen.reason})
          </p>
        )}
        {data.state === "REFUSED" && (
          <p className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            Refused by the question screen: {data.refusal_reason}
          </p>
        )}
        {failed && (
          <p className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            Stage {String(failed.stage)} failed: {String(failed.error)}
          </p>
        )}
      </section>

      <section className="grid grid-cols-3 gap-3 text-sm">
        <Counter label="Crustdata credits" value={`${data.cost.crustdata_credits.toFixed(1)} / ${data.cost.credit_cap}`} />
        <Counter label="Model spend" value={`$${data.cost.model_usd.toFixed(4)}`} />
        <Counter label="Events" value={String(events.length)} />
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Progress</h2>
        <ol className="flex flex-wrap gap-2 text-xs">
          {STAGES.map(([key, label]) => {
            const done = key in data.stages;
            const isFailed = failed?.stage === key;
            const state = isFailed ? "failed" : done ? "done" : running.has(key) ? "running" : "waiting";
            return (
              <li key={key} className={`rounded px-2 py-1 ${STAGE_STYLE[state]}`}>
                {label} · {state}
              </li>
            );
          })}
        </ol>
      </section>

      {subs.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Research plan and panel</h2>
          {subs.map((sq) => (
            <SubQuestionCard key={sq.index} sq={sq} data={data} ranked={panel?.[String(sq.index)]?.ranked} />
          ))}
        </section>
      )}
    </div>
  );
}

const STAGE_STYLE: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  running: "bg-sky-100 text-sky-800 animate-pulse dark:bg-sky-950 dark:text-sky-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  waiting: "bg-zinc-100 text-zinc-500 dark:bg-zinc-900",
};

function Counter({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="font-mono text-base">{value}</div>
    </div>
  );
}

function SubQuestionCard({ sq, data, ranked }: { sq: SubQuestion; data: Case; ranked?: RankedCandidate[] }) {
  const sourced = data.stages.s3_sourcer?.[String(sq.index)];
  const screens = data.stages.s4_people_screen?.[String(sq.index)] ?? [];
  const failed = screens.filter((s) => s.verdict === "fail");
  const companyName = (companyId: number) =>
    sourced?.companies.find((c) => c.chosen?.company_id === companyId)?.chosen?.name ?? "unknown company";

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

      {sourced && (
        <p className="mt-3 text-xs text-zinc-500">
          {sourced.companies.map((c) =>
            c.resolved ? `${c.chosen?.name}: ${c.total_matches ?? "?"} matches` : `${c.asked}: not found in Crustdata`,
          ).join(" · ")}
          {" · "}{sourced.candidates.length} people fetched, {failed.length} excluded by the people screen
        </p>
      )}

      {ranked && ranked.length === 0 && (
        <p className="mt-3 text-sm text-amber-700 dark:text-amber-400">No candidate passed the screen and ranking.</p>
      )}

      {ranked && ranked.length > 0 && (
        <ul className="mt-3 space-y-2">
          {ranked.map((r) => (
            // Customer-safe card: no name, headline, profile URL or location.
            <li key={r.person_id} className="rounded border border-zinc-100 p-3 text-sm dark:border-zinc-900">
              <div className="flex items-center gap-2">
                <span className="font-medium">{r.title ?? "Former employee"}</span>
                <span className="text-zinc-500">· {companyName(r.company_id)}</span>
                {r.tenure_months != null && <span className="text-zinc-500">· {r.tenure_months} months</span>}
                {r.end_date && <span className="text-zinc-500">· left {r.end_date.slice(0, 7)}</span>}
                <span className="ml-auto font-mono">{r.score}</span>
                {r.fit && <span className="rounded bg-zinc-100 px-1.5 text-xs dark:bg-zinc-800">{r.fit}</span>}
                {r.verdict === "review" && (
                  <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                    manual review
                  </span>
                )}
              </div>
              <p className="mt-1 text-zinc-600 dark:text-zinc-400">{r.reason}</p>
              {r.evidence && r.evidence.length > 0 && (
                <p className="mt-1 text-xs text-zinc-500">Evidence: {r.evidence.map((e) => `“${e}”`).join(", ")}</p>
              )}
            </li>
          ))}
        </ul>
      )}

      {failed.length > 0 && (
        <details className="mt-3 text-xs text-zinc-500">
          <summary className="cursor-pointer">Why {failed.length} people were excluded</summary>
          <ul className="mt-2 space-y-1">
            {failed.map((s, i) => (
              <li key={s.person_id}>
                Candidate {i + 1}: {s.results.filter((r) => !r.passed).map((r) => r.reason).join("; ")}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
