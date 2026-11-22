"use client";

// The landing page as a dive: scrolling down descends through Synex's eight stages. Visual language
// (HUD, depth ruler, notched pixel cards, darkening water) inspired by krillion.io; art and content are ours.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { BOTTLE, CHEST, FISH, KRILL, Kelp, LANTERN, PEARL, SMALL_FISH, Sprite } from "./sprites";
import { PearlDiver, ReefFilter } from "./Toys";

type Stage = {
  name: string; title: string; sub: string; body: string; depth: number; tone: string;
  creature: string; line: string; gate?: boolean; art: React.ReactNode; toy?: React.ReactNode; fact?: string;
};

const PINK = { p: "#ff5d8f", H: "#ffd0de", a: "#ff8fb0", l: "#c23d66" };
const CYAN = { b: "#4de3ff", e: "#050a14" };
const GOLD = { g: "#b07a1e", y: "#ffd166", c: "#8a6a3c", w: "#9fd9ff", H: "#ffffff" };

const STAGES: Stage[] = [
  {
    name: "Question screen", title: "Is this question fair to ask?", sub: "secrets get turned back", depth: 40, tone: "text-cyan",
    body: "A small model allows, rewrites or refuses the question, and shows why. Questions after non-public information never go deeper.",
    creature: "LIFEGUARD", line: "Turns back anyone swimming after secrets.", gate: true, fact: "recreational scuba limit · 40m",
    art: <Sprite rows={FISH} palette={{ b: "#ff5d8f", e: "#050a14" }} scale={6} />,
  },
  {
    name: "Plan", title: "Split it into questions people can answer.", sub: "three to five sub-questions", depth: 120, tone: "text-cyan",
    body: "The question becomes 3 to 5 sub-questions, each with the expertise it needs and the companies whose former staff would know.",
    creature: "NAVIGATOR", line: "Charts the route before anyone dives.",
    art: <div className="flex gap-2">{[0, 1, 2].map((i) => <Sprite key={i} rows={SMALL_FISH} palette={CYAN} scale={5} className="bob" style={{ animationDelay: `${i * .3}s` }} />)}</div>,
  },
  {
    name: "Sourcing", title: "Find the people who were there.", sub: "live people data, not a database", depth: 200, tone: "text-violet",
    body: "Crustdata's live people data is searched for people who left the target company in the right window, in the right roles.",
    creature: "SONAR", line: "Pings the deep for people who have left.", fact: "sunlight fades · twilight zone begins · 200m",
    art: (
      <div className="relative h-16 w-16">
        {[0, 0.8, 1.6].map((d) => <span key={d} className="ping absolute inset-0 rounded-full border-2 border-violet" style={{ animationDelay: `${d}s` }} />)}
        <span className="absolute inset-[26px] rounded-full bg-violet shadow-[0_0_16px_#bfa7ff]" />
      </div>
    ),
  },
  {
    name: "People screen", title: "Only the right people get through.", sub: "rules in code, reasons on screen", depth: 332, tone: "text-gold",
    body: "Current employees, people who left too recently or too long ago, short tenures and competitor conflicts are filtered out, each with a stated reason. Try it:",
    creature: "REEF FILTER", line: "Nobody is invited until they pass.", gate: true, fact: "deepest scuba dive on record · 332m",
    art: <Sprite rows={SMALL_FISH} palette={{ b: "#ffd166", e: "#050a14" }} scale={6} className="bob" />, toy: <ReefFilter />,
  },
  {
    name: "Ranking", title: "Who could answer best?", sub: "evidence, checked in code", depth: 500, tone: "text-cyan",
    body: "A small model scores each person against the sub-question and must quote evidence from their profile. Code drops any quote it cannot find.",
    creature: "LANTERNFISH", line: "Lights up the best fit, and shows why.", fact: "emperor penguins dive this deep · 500m",
    art: <Sprite rows={LANTERN} palette={{ b: "#4de3ff", e: "#050a14", y: "#ffd166" }} scale={6} className="bob" />,
  },
  {
    name: "Invitations", title: "Nothing is sent without your click.", sub: "anonymised, approved by you", depth: 700, tone: "text-pink",
    body: "One invitation per expert is drafted. You read the anonymised text and approve. Mail can only reach an allowlist enforced in code.",
    creature: "MESSAGE IN A BOTTLE", line: "Sealed until you say go.", gate: true,
    art: <Sprite rows={BOTTLE} palette={{ c: "#8a6a3c", g: "#4de3ff", w: "#e8f1ff" }} scale={7} className="bob" />,
  },
  {
    name: "Response screen", title: "Keep the pearls. Drop the secrets.", sub: "every answer screened", depth: 1000, tone: "text-ember",
    body: "Each answer is accepted, redacted, held for a team member, or rejected before you see it. Try the code rule:",
    creature: "PEARL DIVER", line: "Nothing confidential reaches the surface.", gate: true, fact: "sperm whales come down here to hunt squid · 1000m",
    art: <Sprite rows={PEARL} palette={{ w: "#e8f1ff", H: "#ffffff" }} scale={8} className="bob" />, toy: <PearlDiver />,
  },
  {
    name: "Memo", title: "One memo. A source on every claim.", sub: "agreement and confidence per sub-question", depth: 1200, tone: "text-gold",
    body: "Accepted answers from the whole panel come together in one memo. A claim without a source is dropped before you see it.",
    creature: "TREASURE", line: "What the panel knows, cited.", fact: "midnight zone · no sunlight at all",
    art: <Sprite rows={CHEST} palette={GOLD} scale={7} className="bob" />,
  },
];

const ANCHORS = [0, ...STAGES.map((s) => s.depth), 1400]; // depth at the centre of each section
const GATES = STAGES.filter((s) => s.gate).length;

const EXAMPLES = [
  "How are unit economics trending in quick commerce?",
  "How do mid-size SaaS companies price enterprise plans?",
  "What is driving churn at consumer fintech apps?",
  "How fast are EV makers cutting battery costs?",
];

const WATER: [number, [number, number, number]][] = [
  [0, [31, 90, 134]], [200, [19, 64, 102]], [500, [12, 41, 69]], [900, [7, 21, 42]], [1400, [5, 10, 20]],
];

function waterAt(depth: number) {
  for (let i = 1; i < WATER.length; i++) {
    const [d1, c1] = WATER[i];
    const [d0, c0] = WATER[i - 1];
    if (depth <= d1) {
      const t = (depth - d0) / (d1 - d0);
      const c = c0.map((v, k) => Math.round(v + (c1[k] - v) * t));
      return `rgb(${c.join(",")})`;
    }
  }
  return "rgb(5,10,20)";
}

const SCHOOLS = [
  { top: 18, dur: 38, delay: 0, n: 3, back: false, glow: false },
  { top: 34, dur: 52, delay: 9, n: 5, back: true, glow: false },
  { top: 58, dur: 44, delay: 4, n: 2, back: false, glow: true },
  { top: 72, dur: 60, delay: 17, n: 4, back: true, glow: false },
  { top: 46, dur: 70, delay: 26, n: 1, back: false, glow: false },
];

const BUBBLES = Array.from({ length: 16 }, (_, i) => ({ left: (i * 37) % 100, size: 4 + (i % 4) * 3, dur: 12 + (i % 6) * 3, delay: (i * 1.7) % 14 }));

export function Landing() {
  const router = useRouter();
  const sections = useRef<(HTMLElement | null)[]>([]);
  const depthText = useRef<HTMLSpanElement>(null);
  const water = useRef<HTMLDivElement>(null);
  const rays = useRef<HTMLDivElement>(null);
  const ruler = useRef<HTMLDivElement>(null);
  const krill = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState(-1);
  const [seen, setSeen] = useState<Set<number>>(new Set());
  const [menu, setMenu] = useState(false);
  const [question, setQuestion] = useState("");
  const [example, setExample] = useState(0);
  const [bursts, setBursts] = useState<{ id: number; x: number; y: number }[]>([]);

  // scroll -> depth, water colour, ruler, current stage
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const mid = window.scrollY + window.innerHeight / 2;
      const centres = sections.current.map((el) => (el ? el.offsetTop + el.offsetHeight / 2 : 0));
      let depth = 0;
      if (mid <= centres[0]) depth = 0;
      else if (mid >= centres[centres.length - 1]) depth = ANCHORS[ANCHORS.length - 1];
      else {
        for (let i = 1; i < centres.length; i++) {
          if (mid <= centres[i]) {
            const t = (mid - centres[i - 1]) / (centres[i] - centres[i - 1]);
            depth = ANCHORS[i - 1] + (ANCHORS[i] - ANCHORS[i - 1]) * t;
            break;
          }
        }
      }
      if (depthText.current) depthText.current.textContent = `${Math.round(depth)}m`;
      if (water.current) water.current.style.background = `linear-gradient(180deg, ${waterAt(depth)} 0%, ${waterAt(depth + 260)} 100%)`;
      if (rays.current) rays.current.style.opacity = String(Math.max(0, 1 - depth / 300));
      if (ruler.current) ruler.current.style.transform = `translateY(${-depth * 1.2}px)`;
      let current = -1;
      sections.current.forEach((el, i) => {
        if (el && i > 0 && el.offsetTop <= mid) current = i - 1;
      });
      setStage(current);
      if (current >= 0) setSeen((s) => (s.has(current) ? s : new Set(s).add(current)));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); cancelAnimationFrame(frame); };
  }, []);

  // the krill follows the pointer, a little behind it
  useEffect(() => {
    if (window.matchMedia("(pointer: coarse)").matches) return;
    let x = 80, y = window.innerHeight * 0.7, tx = x, ty = y, frame = 0, facing = 1;
    const move = (e: PointerEvent) => { tx = e.clientX + 28; ty = e.clientY + 18; };
    const loop = () => {
      const dx = tx - x;
      x += dx * 0.06;
      y += (ty - y) * 0.06;
      if (Math.abs(dx) > 2) facing = dx > 0 ? 1 : -1;
      if (krill.current) krill.current.style.transform = `translate(${x}px, ${y}px) scaleX(${facing})`;
      frame = requestAnimationFrame(loop);
    };
    window.addEventListener("pointermove", move);
    frame = requestAnimationFrame(loop);
    return () => { window.removeEventListener("pointermove", move); cancelAnimationFrame(frame); };
  }, []);

  // cycle example questions in the hero
  useEffect(() => {
    const t = setInterval(() => setExample((e) => (e + 1) % EXAMPLES.length), 3200);
    return () => clearInterval(t);
  }, []);

  const burst = useCallback((x: number, y: number) => {
    const id = Date.now() + Math.random();
    setBursts((b) => [...b, { id, x, y }]);
    setTimeout(() => setBursts((b) => b.filter((p) => p.id !== id)), 1100);
  }, []);

  function dive(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    const box = (e.currentTarget as HTMLElement).getBoundingClientRect();
    burst(box.right - 60, box.top);
    setTimeout(() => router.push(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask"), 450);
  }

  const descend = (i: number) => sections.current[i]?.scrollIntoView({ behavior: "smooth", block: "center" });
  const gatesPassed = STAGES.filter((s, i) => s.gate && seen.has(i)).length;

  return (
    <div className="relative min-h-screen font-sans text-foam" onClick={(e) => burst(e.clientX, e.clientY)}>
      {/* ---- the sea (fixed layers) ---- */}
      <div ref={water} className="fixed inset-0 -z-20" style={{ background: waterAt(0) }} />
      <div ref={rays} className="pointer-events-none fixed inset-0 -z-10 bg-[repeating-linear-gradient(100deg,rgba(255,255,255,.05)_0_60px,transparent_60px_160px)] [mask-image:linear-gradient(180deg,black,transparent_70%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        {BUBBLES.map((b, i) => (
          <span key={i} className="fish absolute bottom-[-20px] rounded-full border border-foam/30"
            style={{ left: `${b.left}%`, width: b.size, height: b.size, animation: `rise ${b.dur}s linear ${b.delay}s infinite` }} />
        ))}
        {SCHOOLS.map((s, i) => (
          <div key={i} className="fish absolute left-0 flex gap-3"
            style={{ top: `${s.top}%`, animation: `${s.back ? "swim-back" : "swim"} ${s.dur}s linear ${s.delay}s infinite` }}>
            {Array.from({ length: s.n }, (_, k) => (
              <Sprite key={k} rows={SMALL_FISH} scale={s.glow ? 4 : 3}
                palette={s.glow ? CYAN : { b: "#06111f", e: "#06111f" }}
                className={s.glow ? "drop-shadow-[0_0_6px_#4de3ff]" : "opacity-70"}
                style={{ transform: `translateY(${(k % 2) * 8}px)` }} />
            ))}
          </div>
        ))}
        <div className="absolute bottom-0 left-0 hidden opacity-80 md:block"><Kelp height={70} seed={2} /></div>
        <div className="absolute bottom-0 left-24 hidden opacity-60 md:block"><Kelp height={44} seed={5} scale={6} /></div>
        <div className="absolute right-12 bottom-0 hidden opacity-80 md:block"><Kelp height={62} seed={7} flip /></div>
      </div>

      {/* ---- the krill ---- */}
      <div ref={krill} className="pointer-events-none fixed top-0 left-0 z-30 hidden md:block" style={{ transform: "translate(80px, 70vh)" }}>
        <Sprite rows={KRILL} palette={PINK} scale={4} className="bob drop-shadow-[0_0_8px_#ff5d8f]" />
      </div>
      {bursts.map((b) => (
        <div key={b.id} className="pointer-events-none fixed z-40" style={{ left: b.x, top: b.y }}>
          {[-24, -10, 0, 12, 26].map((dx, k) => (
            <span key={k} className="burst absolute rounded-full border border-foam/80"
              style={{ width: 6 + (k % 3) * 4, height: 6 + (k % 3) * 4, ["--dx" as string]: `${dx}px`, animation: `burst ${0.8 + k * 0.06}s ease-out forwards` }} />
          ))}
        </div>
      ))}

      {/* ---- HUD ---- */}
      <div className="pointer-events-none fixed inset-x-0 top-0 z-20 flex items-start justify-center gap-4 px-3 pt-3 sm:gap-16">
        <div className="notch scanlines bg-[#0a1628]/90 px-4 py-2 sm:px-6">
          <div className="font-pixel text-sm tracking-[.3em] text-drift">DEPTH</div>
          <span ref={depthText} className="font-pixel text-3xl text-cyan glow-cyan">0m</span>
        </div>
        <div className="flex flex-col items-center gap-1 pt-2">
          <div className="flex gap-1">
            {STAGES.map((_, i) => (
              <span key={i} className={`h-3.5 w-3.5 border transition-colors sm:h-4 sm:w-4 ${i === stage ? "border-pink bg-pink shadow-[0_0_8px_#ff5d8f]" : seen.has(i) ? "border-gold bg-gold" : "border-reef bg-[#0a1628]"}`} />
            ))}
          </div>
          <span className="font-pixel text-sm tracking-[.3em] text-drift">{stage >= 0 ? `STAGE ${stage + 1} OF ${STAGES.length}` : "AT THE SURFACE"}</span>
        </div>
        <div className="notch scanlines bg-[#0a1628]/90 px-4 py-2 text-right sm:px-6">
          <div className="font-pixel text-sm tracking-[.3em] text-drift">GATES</div>
          <span className="font-pixel text-3xl text-pink glow-pink">{gatesPassed}/{GATES}</span>
        </div>
      </div>

      {/* menu */}
      <button onClick={(e) => { e.stopPropagation(); setMenu(true); }} aria-label="Menu"
        className="notch fixed top-20 left-3 z-20 bg-[#0a1628]/90 px-3 py-2 font-pixel text-2xl text-foam hover:text-cyan sm:top-24">≡</button>
      {menu && (
        <div className="fixed inset-0 z-50 bg-abyss/70 backdrop-blur-sm" onClick={(e) => { e.stopPropagation(); setMenu(false); }}>
          <nav className="notch scanlines h-full w-72 bg-[#0a1628] p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <span className="font-pixel text-3xl tracking-[.2em] text-cyan glow-cyan">SYNEX</span>
              <button onClick={() => setMenu(false)} className="font-pixel text-3xl text-drift hover:text-foam">×</button>
            </div>
            <div className="mt-8 flex flex-col gap-4 font-pixel text-2xl tracking-wider">
              <Link href="/ask" className="text-foam hover:text-cyan">▸ Ask a question</Link>
              <button onClick={() => { setMenu(false); descend(1); }} className="text-left text-foam hover:text-cyan">▸ The dive</button>
              <a href="#real" onClick={() => setMenu(false)} className="text-foam hover:text-cyan">▸ What&apos;s real</a>
              <span className="mt-4 text-sm tracking-[.3em] text-drift">OPERATORS</span>
              <Link href="/operator/approvals" className="text-drift hover:text-foam">▸ Operator queue</Link>
              <Link href="/operator/audit" className="text-drift hover:text-foam">▸ Audit trail</Link>
            </div>
          </nav>
        </div>
      )}

      {/* depth ruler */}
      <div className="pointer-events-none fixed top-0 right-0 bottom-0 z-10 hidden w-24 overflow-hidden border-r-2 border-foam/30 md:block">
        <div ref={ruler} className="absolute inset-x-0" style={{ top: "38vh" }}>
          {Array.from({ length: 1400 / 25 + 1 }, (_, i) => i * 25).map((d) => (
            <div key={d} className="absolute right-0 flex items-center gap-1" style={{ top: d * 1.2 }}>
              {d % 100 === 0 && <span className="font-pixel text-sm text-foam/50">-{d}m</span>}
              <span className={`h-px bg-foam/40 ${d % 100 === 0 ? "w-5" : "w-2.5"}`} />
            </div>
          ))}
        </div>
        <div className="absolute right-0 flex items-center gap-1" style={{ top: "38vh" }}>
          <span className="font-pixel text-sm text-pink">YOU</span>
          <span className="h-0.5 w-8 bg-pink" />
          <span className="h-0 w-0 border-y-[6px] border-r-[8px] border-y-transparent border-r-pink" />
        </div>
      </div>

      {/* ---- the surface: hero ---- */}
      <section ref={(el) => { sections.current[0] = el; }} className="relative flex min-h-screen flex-col items-center justify-center px-4 pt-28 pb-16">
        <h1 className="font-pixel text-7xl tracking-[.25em] text-foam glow-cyan sm:text-9xl">SYNEX</h1>
        <p className="mt-2 font-pixel text-xl tracking-[.3em] text-drift sm:text-2xl">ONE QUESTION · A WHOLE PANEL</p>

        <div className="notch scanlines mt-10 w-full max-w-2xl bg-[#0a1628]/90 p-6 sm:p-8">
          <div className="font-pixel text-lg tracking-[.35em] text-pink">ASK ANY BUSINESS QUESTION</div>
          <p key={example} className="pop-in mt-3 min-h-[4.5rem] font-pixel text-3xl leading-tight text-foam sm:text-4xl">
            {EXAMPLES[example]}
          </p>
          <p className="mt-2 font-pixel text-lg tracking-widest text-drift">▼ former employees answer · every claim cited ▼</p>
        </div>

        <form onSubmit={dive} onClick={(e) => e.stopPropagation()} className="mt-6 flex w-full max-w-2xl items-center gap-3">
          <div className="relative hidden h-14 w-14 flex-none sm:block" title="characters typed">
            <svg viewBox="0 0 36 36" className="h-14 w-14 -rotate-90">
              <circle cx="18" cy="18" r="15" fill="#0a1628" stroke="#1b2c47" strokeWidth="3" />
              <circle cx="18" cy="18" r="15" fill="none" stroke="#4de3ff" strokeWidth="3" strokeDasharray={`${Math.min(question.length / 80, 1) * 94} 94`} />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center font-pixel text-lg text-cyan">{question.length}</span>
          </div>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            placeholder="Type your question…"
            className="h-14 min-w-0 flex-1 border-2 border-cyan/60 bg-[#0a1628]/90 px-4 font-pixel text-2xl text-foam caret-pink outline-none placeholder:text-drift/60 focus:border-cyan focus:shadow-[0_0_16px_rgba(77,227,255,.3)]"
          />
          <button type="submit"
            className="h-14 flex-none border-2 border-pink bg-pink px-6 font-pixel text-2xl tracking-[.3em] text-abyss transition hover:shadow-[0_0_24px_rgba(255,93,143,.6)] active:translate-y-0.5">
            DIVE
          </button>
        </form>
        <p className="mt-3 text-center font-pixel text-lg tracking-wider text-drift">
          a model plans the dive · no people data is fetched until you approve the plan
        </p>

        <button onClick={(e) => { e.stopPropagation(); descend(1); }}
          className="mt-14 font-pixel text-2xl tracking-[.3em] text-drift hover:text-cyan">
          descend <span className="inline-block" style={{ animation: "blink 1s steps(1) infinite" }}>▼</span>
        </button>
      </section>

      {/* ---- eight stages down ---- */}
      {STAGES.map((s, i) => (
        <section key={s.name} ref={(el) => { sections.current[i + 1] = el; }}
          className="relative flex min-h-screen flex-col items-center justify-center gap-8 px-4 py-24">
          {s.fact && (
            <div className="pointer-events-none absolute top-16 right-28 hidden items-center gap-3 font-pixel text-lg tracking-wider text-foam/40 lg:flex">
              {s.fact}<span className="h-px w-16 bg-foam/30" />
            </div>
          )}
          <div className="notch scanlines w-full max-w-2xl bg-[#0a1628]/90 p-6 sm:p-8" onClick={(e) => e.stopPropagation()}>
            <div className="font-pixel text-lg tracking-[.35em] text-pink">STAGE {i + 1} OF {STAGES.length} · {s.name.toUpperCase()}</div>
            <h2 className="mt-3 font-pixel text-4xl leading-tight text-foam sm:text-5xl">{s.title}</h2>
            <p className="mt-2 font-pixel text-lg tracking-widest text-drift">▼ {s.sub} ▼</p>
            <p className="mt-4 leading-relaxed text-drift">{s.body}</p>
            {s.toy && <div className="mt-6 border-t border-reef pt-6">{s.toy}</div>}
          </div>

          <div className={`flex flex-col items-center gap-2 text-center ${seen.has(i) ? "pop-in" : "opacity-0"}`}>
            <div className="drop-shadow-[0_0_12px_rgba(77,227,255,.35)]">{s.art}</div>
            <div className={`font-pixel text-5xl tracking-[.2em] ${s.tone} [text-shadow:0_0_18px_currentColor]`}>{s.creature}</div>
            <div className="font-pixel text-2xl text-foam">“{s.line}”</div>
            <div className="font-pixel text-xl tracking-wider">
              {s.gate ? <span className="text-pink">+1 GATE</span> : <span className="text-cyan">STAGE CLEAR</span>}
              <span className="text-foam"> · sink to {s.depth}m</span>
            </div>
          </div>

          <button onClick={(e) => { e.stopPropagation(); descend(i + 2); }}
            className="notch border-2 border-cyan bg-[#0a1628]/90 px-8 py-3 font-pixel text-2xl tracking-[.3em] text-foam transition hover:bg-cyan hover:text-abyss hover:shadow-[0_0_24px_rgba(77,227,255,.5)]">
            {i < STAGES.length - 1 ? "DESCEND ▼" : "REACH THE FLOOR ▼"}
          </button>
        </section>
      ))}

      {/* ---- the sea floor ---- */}
      <section ref={(el) => { sections.current[STAGES.length + 1] = el; }} id="real"
        className="relative flex min-h-screen flex-col items-center justify-center gap-10 px-4 pt-24 pb-0">
        <div className="text-center">
          <div className="font-pixel text-lg tracking-[.35em] text-pink">THE SEA FLOOR · 1400m</div>
          <h2 className="mt-3 font-pixel text-5xl leading-none sm:text-7xl">What&apos;s real down here</h2>
        </div>
        <div className="grid w-full max-w-4xl gap-4 md:grid-cols-3" onClick={(e) => e.stopPropagation()}>
          {[
            ["REAL", "text-cyan", "Crustdata people and company data, Claude model calls, the compliance rules, the audit trail and the cost log. Nothing is pre-loaded or stored for the demo."],
            ["SIMULATED", "text-gold", "Payments. Holds, charges and payouts are a labelled ledger; no money moves."],
            ["TEAMMATES", "text-pink", "Experts are played by our own team: every invitation goes to a teammate's inbox on a local mail server, never to a real person."],
          ].map(([label, tone, text]) => (
            <div key={label} className="notch scanlines bg-[#0a1628]/90 p-6">
              <span className={`font-pixel text-3xl tracking-[.2em] ${tone}`}>{label}</span>
              <p className="mt-3 text-sm leading-relaxed text-drift">{text}</p>
            </div>
          ))}
        </div>
        <Link href="/ask" onClick={(e) => e.stopPropagation()}
          className="notch border-2 border-pink bg-pink px-10 py-4 font-pixel text-3xl tracking-[.3em] text-abyss transition hover:shadow-[0_0_32px_rgba(255,93,143,.6)]">
          START YOUR DIVE
        </Link>
        <button onClick={(e) => { e.stopPropagation(); window.scrollTo({ top: 0, behavior: "smooth" }); }}
          className="font-pixel text-xl tracking-[.3em] text-drift hover:text-cyan">▲ back to the surface</button>
        <footer className="mt-auto w-full border-t border-reef/70 bg-[#030710]">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-5 text-xs text-drift">
            <span className="font-pixel text-2xl tracking-[.2em] text-foam">SYNEX</span>
            <span>Built at ContextCon 05 · Services, Replaced</span>
            <span className="ml-auto">People and company data from Crustdata · Models by Anthropic · Payments simulated</span>
          </div>
        </footer>
      </section>
    </div>
  );
}
