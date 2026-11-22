import Link from "next/link";
import { VT323 } from "next/font/google";

// Landing page. Visual language (deep-sea palette, pixel display font, "descending" depth motif) is
// inspired by krillion.io; every word of content is Synex's own, and every claim matches what the code does.
const pixel = VT323({ weight: "400", subsets: ["latin"], variable: "--font-vt323" });

// Fixed positions so the server and browser render the same bubbles.
const BUBBLES = [
  [6, 9, 0], [14, 5, 4], [23, 7, 9], [31, 4, 2], [42, 8, 6], [55, 5, 11], [63, 9, 3], [71, 6, 8], [79, 4, 1],
  [86, 7, 5], [93, 5, 10], [48, 3, 13],
] as const;

const DEPTHS: { n: string; stage: string; what: string; how: string; tone: string }[] = [
  { n: "01", stage: "Question screen", what: "Refuses or rewrites questions that ask for non-public information.", how: "small model", tone: "text-cyan" },
  { n: "02", stage: "Plan", what: "Splits the question into 3 to 5 sub-questions and the expertise each needs.", how: "small model", tone: "text-cyan" },
  { n: "03", stage: "Sourcing", what: "Finds former employees of the target companies in live Crustdata people data.", how: "Crustdata", tone: "text-violet" },
  { n: "04", stage: "People screen", what: "Current employees, recent leavers, stale exits and competitor conflicts are removed, each with a stated reason.", how: "rules in code", tone: "text-gold" },
  { n: "05", stage: "Ranking", what: "Scores each person against the sub-question, quoting evidence that code checks against the profile.", how: "small model", tone: "text-cyan" },
  { n: "06", stage: "Invitations", what: "Drafts one anonymised invitation per expert. You approve them before anything is sent.", how: "you approve", tone: "text-pink" },
  { n: "07", stage: "Response screen", what: "Every answer is accepted, redacted, held for a person, or rejected before you see it.", how: "model + code rules", tone: "text-ember" },
  { n: "08", stage: "Memo", what: "One memo across all accepted answers, with a source on every claim.", how: "large model", tone: "text-gold" },
];

const RULES = [
  ["Not a current employee", "the profile must show they have left the company"],
  ["Cooling-off", "left at least 6 months ago"],
  ["Freshness", "left no more than 24 months ago"],
  ["Competitor conflict", "a sensitive role at a direct competitor removes them; any other role there is flagged"],
  ["Sensitive former role", "C-suite, legal, finance control or security roles are flagged for review"],
];

const COMPARE = [
  ["Finding experts", "Staff search a database and personal contacts", "Software searches a live people graph by company, role and exit date"],
  ["Vetting", "Manual checks", "Fixed rules in code, each with a stated reason"],
  ["Contact", "One expert, one scheduled call", "A panel invited in parallel; each answers by form in about 10 minutes"],
  ["Output", "Your own call notes", "Screened answers from several experts, each with a source"],
  ["Paper trail", "Opaque", "A hash-chained audit trail and a cost log for every call"],
  ["Pricing", "Per call hour", "Per answered sub-question, held first and charged only when answered"],
];

const REAL = [
  ["Real", "Crustdata people and company data, Claude model calls, the compliance rules, the audit trail and the cost log. Nothing is pre-loaded or stored for the demo."],
  ["Simulated", "Payments. Holds, charges and payouts are a labelled ledger; no money moves."],
  ["Teammates", "Experts are played by our own team: every invitation goes to a teammate's inbox on a local mail server, never to a real person."],
];

export default function Landing() {
  return (
    <div className={`${pixel.variable} relative min-h-screen overflow-hidden bg-abyss font-sans text-foam`}>
      {/* rising bubbles */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        {BUBBLES.map(([left, size, delay], i) => (
          <span
            key={i}
            className="bubble absolute bottom-[-20px] rounded-full border border-cyan/40 bg-cyan/5"
            style={{ left: `${left}%`, width: size, height: size, animation: `rise ${14 + (i % 5) * 3}s linear ${delay}s infinite` }}
          />
        ))}
      </div>

      <header className="relative z-10 border-b border-reef/70">
        <nav className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-4">
          <Link href="/" className="font-pixel text-3xl tracking-[.2em] text-foam glow-cyan">SYNEX</Link>
          <div className="hidden items-center gap-6 text-sm text-drift md:flex">
            <a href="#dive" className="hover:text-foam">How it works</a>
            <a href="#rules" className="hover:text-foam">Compliance</a>
            <a href="#compare" className="hover:text-foam">Why Synex</a>
            <a href="#real" className="hover:text-foam">What&apos;s real</a>
          </div>
          <Link
            href="/ask"
            className="ml-auto rounded-md border border-cyan/60 px-4 py-1.5 font-pixel text-xl tracking-wider text-cyan transition hover:bg-cyan hover:text-abyss hover:shadow-[0_0_24px_rgba(77,227,255,.5)]"
          >
            Dive in →
          </Link>
        </nav>
      </header>

      {/* hero */}
      <section className="depth-wash relative">
        <div className="pixel-grid absolute inset-0 [mask-image:linear-gradient(180deg,black,transparent_85%)]" />
        <div className="relative mx-auto flex max-w-6xl flex-col items-center px-6 pt-24 pb-28 text-center">
          <span className="mb-8 rounded-full border border-reef bg-shallow/70 px-4 py-1 font-pixel text-lg tracking-widest text-drift">
            SERVICES, REPLACED · <span className="text-pink">THE EXPERT NETWORK</span>
          </span>
          <h1 className="font-pixel text-6xl leading-[.95] tracking-wide text-foam sm:text-8xl">
            Ask once.<br />
            <span className="text-cyan glow-cyan">Hear from the people</span><br />
            who were there.
          </h1>
          <p className="mt-8 max-w-2xl text-lg leading-relaxed text-drift">
            Synex finds former employees in live people data, screens every person and every answer with fixed
            compliance rules, and gathers their answers into one memo where every claim cites its source.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link
              href="/ask"
              className="rounded-md bg-cyan px-6 py-3 font-pixel text-2xl tracking-wider text-abyss shadow-[0_0_32px_rgba(77,227,255,.35)] transition hover:shadow-[0_0_48px_rgba(77,227,255,.6)]"
            >
              Ask a question
            </Link>
            <a href="#dive" className="rounded-md border border-reef px-6 py-3 font-pixel text-2xl tracking-wider text-foam transition hover:border-drift">
              See the dive ↓
            </a>
          </div>
          <p className="mt-14 font-pixel text-xl tracking-[.3em] text-drift/70">
            descending<span className="cursor" style={{ animation: "blink 1s steps(1) infinite" }}>_</span>
          </p>
        </div>
      </section>

      {/* data strip */}
      <section className="relative border-y border-reef/70 bg-shallow/40">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-10 gap-y-2 px-6 py-5 font-pixel text-xl tracking-widest text-drift">
          <span>LIVE PEOPLE DATA · <span className="text-foam">CRUSTDATA</span></span>
          <span className="text-reef">◆</span>
          <span>MODELS · <span className="text-foam">CLAUDE</span></span>
          <span className="text-reef">◆</span>
          <span>EVERY CALL <span className="text-gold">LOGGED</span></span>
          <span className="text-reef">◆</span>
          <span>EVERY EVENT <span className="text-pink">HASH-CHAINED</span></span>
        </div>
      </section>

      {/* how it works: the dive */}
      <section id="dive" className="relative mx-auto max-w-6xl scroll-mt-8 px-6 py-24">
        <SectionTitle kicker="How it works" title="Eight stages down" sub="Each stage writes its result and an audit event. You watch it happen live on the case page." />
        <ol className="relative mt-14 border-l border-reef pl-8">
          {DEPTHS.map((d) => (
            <li key={d.n} className="group relative pb-9 last:pb-0">
              <span className="absolute top-1 -left-[41px] flex h-5 w-5 items-center justify-center rounded-full border border-reef bg-abyss">
                <span className={`h-1.5 w-1.5 rounded-full bg-current ${d.tone}`} />
              </span>
              <div className="grid gap-2 rounded-lg border border-reef/80 bg-shallow/40 p-5 transition group-hover:border-drift/60 sm:grid-cols-[110px_1fr_auto] sm:items-center">
                <span className={`font-pixel text-2xl tracking-widest ${d.tone}`}>DEPTH {d.n}</span>
                <div>
                  <h3 className="text-lg font-semibold">{d.stage}</h3>
                  <p className="text-sm leading-relaxed text-drift">{d.what}</p>
                </div>
                <span className="w-fit rounded border border-reef px-2 py-0.5 font-pixel text-lg tracking-wider text-drift">{d.how}</span>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* compliance */}
      <section id="rules" className="relative scroll-mt-8 border-y border-reef/70 bg-shallow/30">
        <div className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-2">
          <div>
            <SectionTitle kicker="Compliance" title="Rules in code, reasons on screen" left
              sub="Nobody is invited until they pass the people screen, and no answer reaches you until it passes the response screen. Every decision is written to the audit trail." />
            <ul className="mt-10 flex flex-col gap-3">
              {RULES.map(([rule, why]) => (
                <li key={rule} className="flex gap-3 rounded-lg border border-reef/80 bg-abyss/60 p-4">
                  <span className="font-pixel text-xl text-gold">✓</span>
                  <div>
                    <span className="font-semibold">{rule}</span>
                    <span className="text-drift"> · {why}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col gap-4">
            <Card tone="border-cyan/40" title="Experts stay anonymous" tag="customer view">
              You see a role, a company, tenure and a reference like <code className="font-pixel text-lg text-cyan">E3fa91c20</code>. Never a
              name, a profile link or an email address.
            </Card>
            <Card tone="border-ember/40" title="Every answer is screened" tag="stage 07">
              Accepted, redacted with the flagged words removed, held for a team member, or rejected. The model must quote
              what it flags, and code checks the quote. Leak phrases are held for a person even if the model let them through.
            </Card>
            <Card tone="border-pink/40" title="Nothing leaves without a click" tag="approval">
              You approve the plan before any data is fetched, and the invitations before any is sent. Mail can only go to
              an allowlist enforced in code.
            </Card>
            <Card tone="border-gold/40" title="An audit trail you can verify" tag="hash chain">
              Each event stores the previous event&apos;s hash. One button recomputes the whole chain and names the first
              changed event, if any.
            </Card>
          </div>
        </div>
      </section>

      {/* comparison */}
      <section id="compare" className="mx-auto max-w-6xl scroll-mt-8 px-6 py-24">
        <SectionTitle kicker="Why Synex" title="An expert network, rebuilt as software" sub="Expert networks sell an hour on the phone with one former employee. Synex sources, vets and asks a whole panel at once." />
        <div className="mt-12 overflow-x-auto rounded-lg border border-reef">
          <div className="min-w-[640px]">
            <div className="grid grid-cols-[160px_1fr_1fr] bg-shallow/60 px-5 py-3 font-pixel text-xl tracking-widest text-drift">
              <span />
              <span>EXPERT NETWORK</span>
              <span className="text-cyan">SYNEX</span>
            </div>
            {COMPARE.map(([aspect, old, ours]) => (
              <div key={aspect} className="grid grid-cols-[160px_1fr_1fr] gap-4 border-t border-reef/70 px-5 py-4 text-sm">
                <span className="font-semibold">{aspect}</span>
                <span className="text-drift">{old}</span>
                <span>{ours}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* what's real */}
      <section id="real" className="scroll-mt-8 border-y border-reef/70 bg-shallow/30">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <SectionTitle kicker="Honesty" title="What's real, what's simulated" sub="Built in seven hours at ContextCon 05. Here is exactly what runs." />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {REAL.map(([label, text], i) => (
              <div key={label} className="rounded-lg border border-reef bg-abyss/60 p-6">
                <span className={`font-pixel text-3xl tracking-widest ${["text-cyan", "text-gold", "text-pink"][i]}`}>{label.toUpperCase()}</span>
                <p className="mt-3 text-sm leading-relaxed text-drift">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* final call to action */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-x-0 bottom-0 h-64 bg-[radial-gradient(ellipse_at_bottom,rgba(77,227,255,.18),transparent_70%)]" />
        <div className="relative mx-auto flex max-w-3xl flex-col items-center px-6 py-28 text-center">
          <h2 className="font-pixel text-5xl leading-none tracking-wide sm:text-7xl">
            One question.<br /><span className="text-pink glow-pink">A whole panel.</span>
          </h2>
          <p className="mt-6 text-drift">Type a business question about any company. Synex plans the research and finds the people.</p>
          <Link
            href="/ask"
            className="mt-10 rounded-md bg-cyan px-8 py-3 font-pixel text-2xl tracking-wider text-abyss shadow-[0_0_32px_rgba(77,227,255,.35)] transition hover:shadow-[0_0_48px_rgba(77,227,255,.6)]"
          >
            Start the dive →
          </Link>
        </div>
      </section>

      <footer className="border-t border-reef/70">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-6 text-xs text-drift">
          <span className="font-pixel text-2xl tracking-[.2em] text-foam">SYNEX</span>
          <span>Built at ContextCon 05 · Services, Replaced</span>
          <span className="ml-auto">People and company data from Crustdata · Models by Anthropic · Payments simulated</span>
        </div>
      </footer>
    </div>
  );
}

function SectionTitle({ kicker, title, sub, left = false }: { kicker: string; title: string; sub: string; left?: boolean }) {
  return (
    <div className={`flex flex-col gap-3 ${left ? "" : "items-center text-center"}`}>
      <span className="font-pixel text-xl tracking-[.3em] text-pink">{kicker.toUpperCase()}</span>
      <h2 className="font-pixel text-5xl leading-none tracking-wide sm:text-6xl">{title}</h2>
      <p className={`max-w-2xl leading-relaxed text-drift ${left ? "" : "mx-auto"}`}>{sub}</p>
    </div>
  );
}

function Card({ title, tag, tone, children }: { title: string; tag: string; tone: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-lg border bg-abyss/60 p-5 ${tone}`}>
      <div className="flex items-center gap-3">
        <h3 className="font-semibold">{title}</h3>
        <span className="ml-auto font-pixel text-lg tracking-wider text-drift">{tag}</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-drift">{children}</p>
    </div>
  );
}
