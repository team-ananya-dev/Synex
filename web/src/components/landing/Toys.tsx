"use client";

// Two hands-on demos for the landing page. They run the same rules as the server, in the browser,
// on whatever the visitor enters. No API call, no stored data, nothing presented as a real case.
import { useState } from "react";

// Defaults of the server's people screen: server/app/jobs/runner.py DEFAULT_PARAMS and
// server/app/stages/s4_people_screen.py (cooling-off, freshness, minimum tenure, not current).
const MIN_LEFT = 6;
const MAX_LEFT = 24;
const MIN_TENURE = 12;

// Same pattern as RISK in server/app/stages/s7_response_screen.py. Keep the two in sync.
const RISK =
  /\b(confidential|nda|non[- ]disclosure|internal (?:document|deck|memo|report|dashboard|email|data|numbers)s?|not (?:yet )?public|unreleased|unannounced|shouldn'?t (?:say|tell|share)|off the record|insider)\b/gi;

function Slider({ label, value, min, max, onChange, unit }: {
  label: string; value: number; min: number; max: number; onChange: (n: number) => void; unit: string;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between font-pixel text-sm tracking-wider text-mist">
        {label}
        <span className="text-lg text-amber">{value} {unit}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="pixel-range w-full"
      />
    </label>
  );
}

export function PeopleScreenToy() {
  const [left, setLeft] = useState(14);
  const [tenure, setTenure] = useState(30);
  const [current, setCurrent] = useState(false);

  const rules: [string, boolean, string][] = [
    ["not a current employee", !current, current ? "still lists the company as a current employer" : "no current role at the company"],
    ["cooling-off", !current && left >= MIN_LEFT, left < MIN_LEFT ? `left ${left} months ago, less than ${MIN_LEFT}` : `left at least ${MIN_LEFT} months ago`],
    ["freshness", left <= MAX_LEFT, left > MAX_LEFT ? `left ${left} months ago, more than ${MAX_LEFT}` : `within ${MAX_LEFT} months`],
    ["minimum tenure", tenure >= MIN_TENURE, tenure < MIN_TENURE ? `${tenure} months there, below ${MIN_TENURE}` : `${tenure} months there`],
  ];
  const pass = rules.every(([, ok]) => ok);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Slider label="left the company" value={left} min={0} max={36} unit="mo ago" onChange={setLeft} />
        <Slider label="time there" value={tenure} min={0} max={60} unit="mo" onChange={setTenure} />
      </div>
      <button
        onClick={() => setCurrent((c) => !c)}
        className={`w-fit border-2 px-3 py-1 font-pixel text-sm tracking-wider transition ${current ? "border-koi text-koi" : "border-rim text-mist hover:text-cream"}`}
      >
        {current ? "■" : "□"} still works there
      </button>
      <div className="relative h-16 overflow-hidden border-2 border-rim bg-pond">
        {/* the reef: a fish swims through when every rule passes, and bounces off when one fails */}
        <div className="absolute top-0 bottom-0 left-1/2 w-3 -translate-x-1/2 bg-[repeating-linear-gradient(180deg,#2a8746_0_6px,transparent_6px_10px)]" />
        <div key={`${pass}-${left}-${tenure}-${current}`} className={`absolute top-1/2 -translate-y-1/2 ${pass ? "swim-through" : "bounce-off"}`}>
          <span className={`font-pixel text-2xl ${pass ? "text-amber" : "text-koi"}`}>{"><>"}</span>
        </div>
      </div>
      <ul className="flex flex-col gap-1 text-sm">
        {rules.map(([name, ok, why]) => (
          <li key={name} className={ok ? "text-cream" : "text-koi"}>
            {ok ? "✓" : "✗"} {name} <span className="text-mist">· {why}</span>
          </li>
        ))}
      </ul>
      <p className={`font-pixel text-2xl tracking-wider ${pass ? "text-leaf" : "text-koi"}`}>
        {pass ? "Passes the screen" : "Filtered out"}
      </p>
      <p className="text-xs text-mist">Same thresholds as the server&apos;s people screen (default settings), run in your browser.</p>
    </div>
  );
}

const SAMPLE = "Delivery times dropped a lot after they opened more dark stores. I shouldn't say this, but the internal deck showed a loss.";

export function LeakRuleToy() {
  const [text, setText] = useState(SAMPLE);
  const hits = [...text.matchAll(RISK)];
  const parts: { t: string; hit: boolean }[] = [];
  let at = 0;
  for (const m of hits) {
    if (m.index! > at) parts.push({ t: text.slice(at, m.index), hit: false });
    parts.push({ t: m[0], hit: true });
    at = m.index! + m[0].length;
  }
  if (at < text.length) parts.push({ t: text.slice(at), hit: false });

  return (
    <div className="flex flex-col gap-4">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        maxLength={600}
        className="w-full resize-none border-2 border-rim bg-pond p-3 text-sm leading-relaxed text-cream outline-none focus:border-amber"
        placeholder="Type an expert's answer…"
      />
      <p className="min-h-[3.5rem] border-2 border-rim bg-pond/60 p-3 text-sm leading-relaxed text-mist">
        {parts.map((p, i) => p.hit
          ? <mark key={i} className="bg-koi/25 px-0.5 text-koi">{p.t}</mark>
          : <span key={i}>{p.t}</span>)}
      </p>
      <p className={`font-pixel text-2xl tracking-wider ${hits.length ? "text-amber" : "text-leaf"}`}>
        {hits.length ? `Held for a person · ${hits.length} flag${hits.length > 1 ? "s" : ""}` : "Clear · on to the model screen"}
      </p>
      <p className="text-xs text-mist">
        This runs only the code rule, in your browser. On the server a model screen also reads every answer, and its
        quotes are checked in code.
      </p>
    </div>
  );
}
