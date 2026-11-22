"use client";

// Landing page over a live pixel koi pond (Pond.tsx, fixed behind the page). The pond is the only playful
// element; type and controls are minimal. Every claim on the page matches what the code does.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pond, pondDrop } from "./Pond";
import { LeakRuleToy, PeopleScreenToy } from "./Toys";

const STAGES: { name: string; what: string; how: string }[] = [
  { name: "Question screen", what: "Allows, rewrites or refuses the question, and says why. Requests for non-public information stop here.", how: "Model" },
  { name: "Plan", what: "Splits the question into 3 to 5 sub-questions, the expertise each needs and the companies whose former staff would know.", how: "Model" },
  { name: "Sourcing", what: "Searches Crustdata's live people data for people who left those companies in the right window and roles.", how: "Crustdata" },
  { name: "People screen", what: "Removes current employees, recent leavers, stale exits, short tenures and competitor conflicts, each with a stated reason.", how: "Rules in code" },
  { name: "Ranking", what: "Scores each person against the sub-question. The model must quote evidence from the profile, and code drops quotes it cannot find.", how: "Model" },
  { name: "Invitations", what: "One anonymised invitation per expert. You approve them before anything is sent, and mail can only reach an allowlist.", how: "Your approval" },
  { name: "Response screen", what: "Every answer is accepted, redacted, held for a team member, or rejected before you see it.", how: "Model + rules" },
  { name: "Memo", what: "Accepted answers from the whole panel in one memo, with a source on every claim. Claims without one are dropped.", how: "Model" },
];

const PRINCIPLES = [
  ["Experts stay anonymous", "You see a role, a company and tenure. Never a name, a profile link or an email address."],
  ["Nothing leaves without approval", "You approve the plan before any people data is fetched, and the invitations before any is sent."],
  ["Every answer is screened", "The model must quote what it flags and code checks the quote. Leak phrases are held for a person."],
  ["A verifiable audit trail", "Each event stores the previous event's hash. One action recomputes the whole chain."],
];

const COMPARE = [
  ["Finding experts", "Staff search a database and personal contacts", "Software searches live people data by company, role and exit date"],
  ["Vetting", "Manual checks", "Fixed rules in code, each with a stated reason"],
  ["Contact", "One expert, one scheduled call", "A panel invited at once; each answers a short form"],
  ["Paper trail", "Opaque", "A hash-chained audit trail and a cost log for every call"],
  ["Pricing", "Per call hour", "Per answered sub-question, held first and charged only when answered"],
];

const REAL = [
  ["Real", "Crustdata people and company data, Claude model calls, the compliance rules, the audit trail and the cost log. Nothing is pre-loaded or stored for the demo."],
  ["Simulated", "Payments. Holds, charges and payouts are a labelled ledger; no money moves."],
  ["Played by the team", "Experts are played by our own team: every invitation goes to a teammate's inbox on a local mail server, never to a real person."],
];

export function Landing() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  function start(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const r = e.currentTarget.getBoundingClientRect();
    pondDrop(r.left + r.width / 2, r.top + r.height / 2, 1.2);
    const q = question.trim();
    setTimeout(() => router.push(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask"), 350);
  }

  return (
    <div className="relative min-h-screen font-sans text-cream">
      <Pond />

      <header className="relative z-10">
        <nav className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-6">
          <Link href="/" className="font-serif text-2xl tracking-tight text-cream">Synex</Link>
          <div className="hidden items-center gap-7 text-sm text-mist md:flex">
            <a href="#how" className="transition-colors hover:text-cream">How it works</a>
            <a href="#rules" className="transition-colors hover:text-cream">Rules</a>
            <a href="#real" className="transition-colors hover:text-cream">What&apos;s real</a>
          </div>
          <Link href="/ask" className="btn-ghost ml-auto">Start research</Link>
        </nav>
      </header>

      <section className="relative flex min-h-[86vh] flex-col items-center justify-center px-6 text-center">
        <span className="eyebrow mb-7">An expert network, as software</span>
        <h1 className="max-w-4xl font-serif text-5xl leading-[1.05] tracking-tight text-cream soft-shadow sm:text-7xl">
          One question. Answers from <em className="text-amber">the people who were there.</em>
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-relaxed text-cream/75 soft-shadow">
          Synex finds former employees in live people data, screens every person and every answer with fixed
          compliance rules, and brings their answers back with a source on every claim.
        </p>
        <form onSubmit={start} className="glass mt-10 flex w-full max-w-2xl items-center gap-2 rounded-full p-1.5 pl-5">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            placeholder="Ask a business question about any company"
            className="h-11 min-w-0 flex-1 bg-transparent text-[15px] text-cream outline-none placeholder:text-mist/70"
          />
          <button type="submit" className="btn-primary flex-none">Start research</button>
        </form>
        <p className="mt-4 text-xs text-mist soft-shadow">
          A model plans the research first. No people data is fetched until you approve the plan.
        </p>
      </section>

      <section id="how" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading eyebrow="How it works" title="Eight stages, from question to answers" />
        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-white/8 bg-white/8 sm:grid-cols-2 lg:grid-cols-4">
          {STAGES.map((s, i) => (
            <div key={s.name} className="flex flex-col gap-2 bg-[#060b15]/90 p-6 backdrop-blur-md">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-xs text-mist">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-[11px] text-mist/80">{s.how}</span>
              </div>
              <h3 className="mt-2 text-[15px] font-medium text-cream">{s.name}</h3>
              <p className="text-sm leading-relaxed text-mist">{s.what}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-mist soft-shadow">
          Every stage writes its result and an audit event, and the case page shows each one as it happens.
        </p>
      </section>

      <section id="rules" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading eyebrow="The rules" title="Try two of them yourself" sub="These run the same thresholds and patterns as the server, in your browser, on what you enter." />
        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <div className="glass rounded-2xl p-7">
            <span className="eyebrow">People screen</span>
            <h3 className="mt-3 font-serif text-3xl tracking-tight">Would this person be invited?</h3>
            <div className="mt-6"><PeopleScreenToy /></div>
          </div>
          <div className="glass rounded-2xl p-7">
            <span className="eyebrow">Response screen</span>
            <h3 className="mt-3 font-serif text-3xl tracking-tight">Would this answer get through?</h3>
            <div className="mt-6"><LeakRuleToy /></div>
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-6 py-24">
        <Heading eyebrow="Why Synex" title="Built for compliance from the first step" />
        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {PRINCIPLES.map(([title, text]) => (
            <div key={title} className="glass rounded-2xl p-6">
              <h3 className="text-[15px] font-medium">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mist">{text}</p>
            </div>
          ))}
        </div>
        <div className="glass mt-6 overflow-x-auto rounded-2xl">
          <div className="min-w-[640px]">
            <div className="grid grid-cols-[160px_1fr_1fr] px-6 py-4 text-xs text-mist">
              <span />
              <span>Traditional expert network</span>
              <span className="text-cream">Synex</span>
            </div>
            {COMPARE.map(([aspect, old, ours]) => (
              <div key={aspect} className="grid grid-cols-[160px_1fr_1fr] gap-4 border-t border-white/8 px-6 py-4 text-sm">
                <span className="font-medium">{aspect}</span>
                <span className="text-mist">{old}</span>
                <span>{ours}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="real" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading eyebrow="Transparency" title="What's real, and what's simulated" />
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {REAL.map(([label, text]) => (
            <div key={label} className="glass rounded-2xl p-6">
              <h3 className="font-serif text-2xl tracking-tight">{label}</h3>
              <p className="mt-3 text-sm leading-relaxed text-mist">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="relative flex flex-col items-center px-6 py-28 text-center">
        <h2 className="max-w-3xl font-serif text-4xl leading-tight tracking-tight soft-shadow sm:text-6xl">
          Ask once. <em className="text-amber">Hear from a whole panel.</em>
        </h2>
        <Link href="/ask" className="btn-primary mt-10">Start research</Link>
      </section>

      <footer className="relative border-t border-white/8 bg-[#04070d]/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-6 text-xs text-mist">
          <span className="font-serif text-lg text-cream">Synex</span>
          <span>Built at ContextCon 05</span>
          <span className="ml-auto">People and company data from Crustdata · Models by Anthropic · Payments simulated</span>
        </div>
      </footer>
    </div>
  );
}

function Heading({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <span className="eyebrow">{eyebrow}</span>
      <h2 className="max-w-3xl font-serif text-4xl leading-tight tracking-tight soft-shadow sm:text-5xl">{title}</h2>
      {sub && <p className="max-w-xl text-sm leading-relaxed text-mist soft-shadow">{sub}</p>}
    </div>
  );
}
