"use client";

// Expert page: opened from the private link in an approved outreach email. A teammate answers here
// in the persona of the candidate. It never shows the customer, other experts or contact details.
// Steps: landing (rules + attestations) -> answers -> review -> submitted. Answers are final once sent.
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ATTESTATIONS, type AnswerKind, type Confidence, type ExpertPage } from "@/lib/api";

type Draft = { kind: AnswerKind; text: string; confidence: Confidence | null };
type Step = "landing" | "form" | "review" | "done";

const KIND_OPTIONS: [AnswerKind, string][] = [
  ["dont_know", "I don't know"],
  ["confidential", "I can't answer without sharing confidential information"],
];

export function ExpertView() {
  const { token } = useParams<{ token: string }>();
  const [page, setPage] = useState<ExpertPage | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("landing");
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  const [reconfirm, setReconfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getExpertPage(token).then(setPage).catch((e) => setLoadError(e.message));
  }, [token]);

  return (
    <div className="flex min-h-screen justify-center bg-background">
      <div className="box-border flex min-h-screen w-full max-w-[520px] flex-col">
        <div className="flex items-center gap-2.5 border-b border-line px-[22px] py-4">
          <span className="text-base font-semibold">Synex</span>
          <span className="ml-auto font-mono text-[11px] text-zinc-500">private link · no login</span>
        </div>
        {renderBody()}
      </div>
    </div>
  );

  function renderBody() {
    if (loadError) return <Closed title="This link is not active" text={loadError.startsWith("404") ? "This link is not valid." : loadError} />;
    if (!page) return <p className="px-[22px] py-10 text-sm text-zinc-500">Loading…</p>;
    if (!page.available) return <Closed title="This link is not active" text={page.reason} />;
    if (step === "done" || page.submitted) {
      return (
        <Closed
          title="Thank you"
          text="Your answers were received. Each one is screened before it is used, and answers rejected for confidentiality are not paid. Payout is simulated: no money moves."
        />
      );
    }

    const { persona, subquestions } = page;
    const draft = (i: number): Draft => drafts[i] ?? { kind: "answer", text: "", confidence: null };
    const setDraft = (i: number, patch: Partial<Draft>) => setDrafts((d) => ({ ...d, [i]: { ...draft(i), ...patch } }));
    const roleLine = [persona.role, persona.company && `at ${persona.company}`].filter(Boolean).join(" ") || "former employee";
    const allTicked = ATTESTATIONS.every(([k]) => ticks[k]);
    const complete = subquestions.every((s) => {
      const d = draft(s.index);
      return d.kind !== "answer" || (d.text.trim().length >= 2 && d.confidence);
    });

    async function submit() {
      setBusy(true);
      setError(null);
      try {
        await api.submitResponses(token, {
          mode: "form",
          attestations: ticks,
          answers: subquestions.map((s) => ({ index: s.index, ...draft(s.index) })),
        });
        setStep("done");
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setBusy(false);
      }
    }

    return (
      <>
        <div className="border-b border-[#2a1d08] bg-[#120c04] px-[22px] py-2.5 text-xs leading-normal text-amber-300">
          Teammate routing: you are answering as <b className="font-medium">{page.first_name ?? "this expert"}</b> ({roleLine}). The
          customer never sees this name.
        </div>

        {step === "landing" && (
          <div className="flex flex-1 flex-col gap-[18px] p-[22px]">
            <div className="flex flex-col gap-2">
              <span className="text-xs text-zinc-400">A short research request{page.first_name ? ` for ${page.first_name}` : ""}</span>
              <span className="text-[23px] leading-tight font-semibold tracking-[-.01em] text-pretty">
                {subquestions.length} short question{subquestions.length === 1 ? "" : "s"} about how the business worked
              </span>
              <span className="text-[13px] leading-relaxed text-zinc-400">
                We found your public professional profile ({roleLine}). We never tell you who the client is, and your name
                is never shown to them.
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Stat value={`$${page.payout.per_accepted_answer.toFixed(0)}`} label="per accepted answer · simulated" />
              <Stat value="~10 min" label="by form" />
            </div>
            <div className="flex flex-col gap-1.5 text-[13px] leading-normal text-zinc-300">
              <span className="text-[11px] uppercase tracking-[.06em] text-zinc-500">Ground rules</span>
              <span>Nothing confidential or covered by an NDA.</span>
              <span>Nothing non-public about the company&apos;s finances.</span>
              <span>Every answer is screened. Answers rejected for confidentiality are not paid.</span>
            </div>
            <div className="flex flex-col gap-2.5 text-sm">
              {ATTESTATIONS.map(([key, label]) => (
                <Check key={key} on={!!ticks[key]} onToggle={() => setTicks((t) => ({ ...t, [key]: !t[key] }))}>{label}</Check>
              ))}
            </div>
            <div className="mt-auto flex flex-col gap-2 pt-3">
              <button
                onClick={() => setStep("form")}
                disabled={!allTicked}
                className="rounded-lg bg-foreground p-[13px] text-[15px] font-medium text-background disabled:opacity-40"
              >
                Accept and continue
              </button>
            </div>
          </div>
        )}

        {step === "form" && (
          <>
            <div className="h-[3px] bg-line"><div className="h-[3px] w-1/2 bg-violet-400" /></div>
            <div className="flex flex-col gap-[26px] p-[22px]">
              <span className="text-xl font-semibold">Your answers</span>
              {subquestions.map((s, n) => {
                const d = draft(s.index);
                return (
                  <div key={s.index} className="flex flex-col gap-2.5">
                    <span className="font-mono text-xs text-zinc-500">Question {n + 1} of {subquestions.length}</span>
                    <span className="text-[17px] leading-snug font-semibold text-pretty">{s.text}</span>
                    {d.kind === "answer" && (
                      <>
                        <textarea
                          value={d.text}
                          onChange={(e) => setDraft(s.index, { text: e.target.value })}
                          rows={5}
                          maxLength={6000}
                          placeholder="In your own words. Ranges and how things worked are ideal; no internal numbers or documents."
                          className="resize-y rounded-lg border border-zinc-700 bg-panel p-3 text-sm leading-normal outline-none focus:border-zinc-500"
                        />
                        <div className="flex items-center gap-2.5 text-[13px] text-zinc-400">
                          <span>How sure are you?</span>
                          <div className="flex overflow-hidden rounded-md border border-zinc-800">
                            {(["low", "medium", "high"] as Confidence[]).map((c) => (
                              <button
                                key={c}
                                onClick={() => setDraft(s.index, { confidence: c })}
                                className={`px-3 py-1.5 text-[13px] ${d.confidence === c ? "bg-foreground text-background" : "text-zinc-400 hover:bg-hover"}`}
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                    <div className="flex flex-col gap-1.5 text-[13px]">
                      {KIND_OPTIONS.map(([kind, label]) => {
                        const on = d.kind === kind;
                        return (
                          <button
                            key={kind}
                            onClick={() => setDraft(s.index, { kind: on ? "answer" : kind })}
                            className={`flex items-center gap-2 text-left ${on ? "text-foreground" : "text-zinc-500"}`}
                          >
                            <span className={`h-3 w-3 rounded-full border ${on ? "border-foreground bg-foreground" : "border-zinc-600"}`} />
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
              <div className="flex gap-2">
                <button onClick={() => setStep("landing")} className="flex-1 rounded-lg border border-zinc-700 p-[13px] text-sm">Back</button>
                <button
                  onClick={() => setStep("review")}
                  disabled={!complete}
                  className="flex-[2] rounded-lg bg-foreground p-[13px] text-[15px] font-medium text-background disabled:opacity-40"
                >
                  Review
                </button>
              </div>
            </div>
          </>
        )}

        {step === "review" && (
          <div className="flex flex-col gap-4 p-[22px]">
            <span className="text-xl font-semibold">What the customer will see</span>
            <span className="text-[13px] leading-normal text-zinc-400">
              Shown with your former role only. No name, no contact details. Go back and edit anything you want removed
              before submitting; answers cannot be changed afterwards.
            </span>
            {subquestions.map((s) => {
              const d = draft(s.index);
              return (
                <div key={s.index} className="flex flex-col gap-1.5 rounded-lg border border-zinc-800 p-3.5">
                  <span className="text-xs text-zinc-500">{s.text}</span>
                  <span className={`text-sm leading-relaxed whitespace-pre-wrap ${d.kind === "answer" ? "text-foreground" : "text-zinc-500"}`}>
                    {d.kind === "answer" ? d.text : KIND_OPTIONS.find(([k]) => k === d.kind)?.[1]}
                  </span>
                  {d.kind === "answer" && <span className="text-[11px] text-zinc-500">confidence: {d.confidence}</span>}
                </div>
              );
            })}
            <Check on={reconfirm} onToggle={() => setReconfirm((v) => !v)}>
              I confirm again: nothing here is confidential or non-public.
            </Check>
            {error && <span className="text-[13px] text-red-300">{error}</span>}
            <div className="flex gap-2">
              <button onClick={() => setStep("form")} className="flex-1 rounded-lg border border-zinc-700 p-[13px] text-sm">Edit</button>
              <button
                onClick={submit}
                disabled={busy || !reconfirm}
                className="flex-[2] rounded-lg bg-foreground p-[13px] text-[15px] font-medium text-background disabled:opacity-40"
              >
                {busy ? "Submitting…" : "Submit"}
              </button>
            </div>
          </div>
        )}
      </>
    );
  }
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-zinc-800 px-3 py-2.5">
      <span className="font-mono text-lg font-medium">{value}</span>
      <span className="text-[11px] text-zinc-500">{label}</span>
    </div>
  );
}

function Check({ on, onToggle, children }: { on: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onToggle} className="flex items-start gap-2.5 text-left leading-snug">
      <span className={`mt-px flex h-[17px] w-[17px] flex-none items-center justify-center rounded border text-[11px] text-background ${on ? "border-foreground bg-foreground" : "border-zinc-600"}`}>
        {on && "✓"}
      </span>
      <span>{children}</span>
    </button>
  );
}

function Closed({ title, text }: { title: string; text: string }) {
  return (
    <div className="flex flex-col gap-2.5 px-[22px] py-10">
      <span className="text-xl font-semibold">{title}</span>
      <span className="text-sm leading-relaxed text-zinc-400">{text}</span>
    </div>
  );
}
