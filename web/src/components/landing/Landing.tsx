"use client";

// Landing page over a live pixel koi pond. The pond (Pond.tsx) is fixed behind the page and reacts to the
// pointer everywhere; buttons and cards drop stones into it. Every claim on the page matches what the code does.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pond, pondDrop } from "./Pond";
import { LeakRuleToy, PeopleScreenToy } from "./Toys";

const STAGES: { name: string; what: string; how: string; tone: string }[] = [
  { name: "Question screen", what: "Allows, rewrites or refuses the question, and says why. Requests for non-public information stop here.", how: "small model", tone: "text-petal" },
  { name: "Plan", what: "Splits the question into 3 to 5 sub-questions, the expertise each needs and the companies whose former staff would know.", how: "small model", tone: "text-petal" },
  { name: "Sourcing", what: "Searches Crustdata's live people data for people who left those companies in the right window and roles.", how: "Crustdata", tone: "text-leaf" },
  { name: "People screen", what: "Removes current employees, recent leavers, stale exits, short tenures and competitor conflicts, each with a stated reason.", how: "rules in code", tone: "text-amber" },
  { name: "Ranking", what: "Scores each person against the sub-question. The model must quote evidence from the profile, and code drops quotes it cannot find.", how: "small model", tone: "text-petal" },
  { name: "Invitations", what: "One anonymised invitation per expert. You read them and approve before anything is sent, and mail can only reach an allowlist.", how: "you approve", tone: "text-koi" },
  { name: "Response screen", what: "Every answer is accepted, redacted, held for a team member, or rejected before you see it.", how: "model + code rules", tone: "text-amber" },
  { name: "Memo", what: "Accepted answers from the whole panel in one memo, with a source on every claim. Claims without one are dropped.", how: "large model", tone: "text-koi" },
];

const COMPARE = [
  ["Finding experts", "Staff search a database and personal contacts", "Software searches live people data by company, role and exit date"],
  ["Vetting", "Manual checks", "Fixed rules in code, each with a stated reason"],
  ["Contact", "One expert, one scheduled call", "A panel invited at once; each answers a short form"],
  ["Paper trail", "Opaque", "A hash-chained audit trail and a cost log for every call"],
  ["Pricing", "Per call hour", "Per answered sub-question, held first and charged only when answered"],
];

const REAL = [
  ["Real", "text-leaf", "Crustdata people and company data, Claude model calls, the compliance rules, the audit trail and the cost log. Nothing is pre-loaded or stored for the demo."],
  ["Simulated", "text-amber", "Payments. Holds, charges and payouts are a labelled ledger; no money moves."],
  ["Teammates", "text-koi", "Experts are played by our own team: every invitation goes to a teammate's inbox on a local mail server, never to a real person."],
];

const centre = (el: HTMLElement) => {
  const r = el.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2] as const;
};

export function Landing() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  function drop(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const button = e.currentTarget.querySelector("button");
    if (button) pondDrop(...centre(button), 1.6);
    const q = question.trim();
    setTimeout(() => router.push(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask"), 500);
  }

  const ripple = (e: React.MouseEvent<HTMLElement>) => pondDrop(...centre(e.currentTarget), 0.5);

  return (
    <div className="relative min-h-screen text-cream">
      <Pond />

      <header className="relative z-10">
        <nav className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-5">
          <Link href="/" className="flex items-center gap-2 font-pixel text-2xl text-cream text-pond-shadow">
            <span className="inline-block h-3 w-3 bg-koi shadow-[2px_2px_0_#070d19]" />synex
          </Link>
          <div className="hidden items-center gap-6 text-sm text-mist md:flex">
            <a href="#how" className="hover:text-cream">How it works</a>
            <a href="#try" className="hover:text-cream">Try the rules</a>
            <a href="#real" className="hover:text-cream">What&apos;s real</a>
          </div>
          <Link href="/ask" onMouseEnter={ripple} className="pixel-btn ml-auto bg-deep px-4 py-1.5 font-pixel text-sm text-amber">
            Ask a question
          </Link>
        </nav>
      </header>

      {/* hero: open water in the middle of the pond */}
      <section className="relative flex min-h-[88vh] flex-col items-center justify-center px-6 text-center">
        <span className="pixel-panel mb-8 px-3 py-1 font-pixel text-xs tracking-widest text-mist">
          SERVICES, REPLACED · <span className="text-amber">AN EXPERT NETWORK AS SOFTWARE</span>
        </span>
        <h1 className="max-w-4xl font-pixel text-5xl leading-[1.05] text-cream text-pond-shadow sm:text-7xl">
          Drop one question.<br />
          <span className="text-amber">Watch it ripple out</span> to a whole panel.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-cream/85 text-pond-shadow">
          Synex finds former employees in live people data, screens every person and every answer with fixed
          compliance rules, and brings their answers back with a source on every claim.
        </p>
        <form onSubmit={drop} className="pixel-panel mt-10 flex w-full max-w-2xl items-center gap-2 p-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            placeholder="How are unit economics trending in quick commerce?"
            className="h-12 min-w-0 flex-1 bg-transparent px-3 text-base text-cream outline-none placeholder:text-mist/60"
          />
          <button type="submit" className="pixel-btn h-12 flex-none bg-koi px-5 font-pixel text-base text-cream">
            Drop it
          </button>
        </form>
        <p className="mt-3 text-xs text-mist text-pond-shadow">
          A model plans the research first · no people data is fetched until you approve the plan
        </p>
        <p className="mt-12 font-pixel text-xs tracking-widest text-mist/80 text-pond-shadow">
          move your cursor across the water · click to drop a stone
        </p>
      </section>

      {/* how it works */}
      <section id="how" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading kicker="How it works" title="Eight stages, from question to answers" />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STAGES.map((s, i) => (
            <div key={s.name} onMouseEnter={ripple} className="pixel-panel group flex flex-col gap-2 p-5 transition hover:-translate-y-1 hover:border-amber/60">
              <div className="flex items-baseline justify-between">
                <span className={`font-pixel text-3xl ${s.tone}`}>{String(i + 1).padStart(2, "0")}</span>
                <span className="border border-rim px-1.5 py-0.5 font-pixel text-[10px] tracking-wider text-mist">{s.how}</span>
              </div>
              <h3 className="font-pixel text-lg">{s.name}</h3>
              <p className="text-sm leading-relaxed text-mist">{s.what}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-mist text-pond-shadow">
          Every stage writes its result and an audit event. You watch it happen live on the case page.
        </p>
      </section>

      {/* try the rules */}
      <section id="try" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading kicker="Try the rules" title="Two of the real rules, in your browser" />
        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <div className="pixel-panel p-6">
            <div className="font-pixel text-xs tracking-widest text-amber">STAGE 04 · PEOPLE SCREEN</div>
            <h3 className="mt-2 font-pixel text-2xl">Would this person be invited?</h3>
            <div className="mt-6"><PeopleScreenToy /></div>
          </div>
          <div className="pixel-panel p-6">
            <div className="font-pixel text-xs tracking-widest text-amber">STAGE 07 · RESPONSE SCREEN</div>
            <h3 className="mt-2 font-pixel text-2xl">Would this answer get through?</h3>
            <div className="mt-6"><LeakRuleToy /></div>
          </div>
        </div>
      </section>

      {/* compliance and comparison */}
      <section className="relative mx-auto max-w-6xl px-6 py-24">
        <Heading kicker="Why Synex" title="An expert network, rebuilt as software" />
        <div className="mt-12 grid gap-4 md:grid-cols-4">
          {[
            ["Experts stay anonymous", "You see a role, a company, tenure and a reference like E3fa91c20. Never a name, a profile link or an email."],
            ["Nothing leaves without a click", "You approve the plan before any people data is fetched, and the invitations before any is sent."],
            ["Answers are screened", "The model must quote what it flags and code checks the quote. Leak phrases are held for a person."],
            ["An audit trail you can verify", "Each event stores the previous event's hash. One button recomputes the chain."],
          ].map(([title, text]) => (
            <div key={title} onMouseEnter={ripple} className="pixel-panel p-5">
              <h3 className="font-pixel text-base text-amber">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mist">{text}</p>
            </div>
          ))}
        </div>
        <div className="pixel-panel mt-8 overflow-x-auto">
          <div className="min-w-[640px]">
            <div className="grid grid-cols-[150px_1fr_1fr] px-5 py-3 font-pixel text-xs tracking-widest text-mist">
              <span />
              <span>EXPERT NETWORK</span>
              <span className="text-amber">SYNEX</span>
            </div>
            {COMPARE.map(([aspect, old, ours]) => (
              <div key={aspect} className="grid grid-cols-[150px_1fr_1fr] gap-4 border-t-2 border-rim px-5 py-3.5 text-sm">
                <span className="font-pixel text-sm">{aspect}</span>
                <span className="text-mist">{old}</span>
                <span>{ours}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* what's real */}
      <section id="real" className="relative mx-auto max-w-6xl scroll-mt-6 px-6 py-24">
        <Heading kicker="Honesty" title="What's real, what's simulated" />
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {REAL.map(([label, tone, text]) => (
            <div key={label} onMouseEnter={ripple} className="pixel-panel p-6">
              <span className={`font-pixel text-2xl ${tone}`}>{label}</span>
              <p className="mt-3 text-sm leading-relaxed text-mist">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* closing */}
      <section className="relative flex flex-col items-center px-6 py-28 text-center">
        <h2 className="font-pixel text-4xl text-pond-shadow sm:text-6xl">
          One question.<br /><span className="text-koi">A whole panel.</span>
        </h2>
        <Link href="/ask" onMouseEnter={ripple} className="pixel-btn mt-10 bg-koi px-8 py-3 font-pixel text-xl text-cream">
          Drop your question
        </Link>
      </section>

      <footer className="relative border-t-2 border-rim bg-deep/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-5 text-xs text-mist">
          <span className="font-pixel text-lg text-cream">synex</span>
          <span>Built at ContextCon 05 · Services, Replaced</span>
          <span className="ml-auto">People and company data from Crustdata · Models by Anthropic · Payments simulated · Pond drawn in code</span>
        </div>
      </footer>
    </div>
  );
}

function Heading({ kicker, title }: { kicker: string; title: string }) {
  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <span className="font-pixel text-xs tracking-[.3em] text-amber text-pond-shadow">{kicker.toUpperCase()}</span>
      <h2 className="font-pixel text-4xl leading-tight text-pond-shadow sm:text-5xl">{title}</h2>
    </div>
  );
}
