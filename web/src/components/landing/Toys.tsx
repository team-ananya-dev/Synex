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
    <label className="flex flex-col gap-2.5">
      <span className="flex items-baseline justify-between text-xs text-mist">
        {label}
        <span className="font-mono text-sm text-cream">{value} {unit}</span>
      </span>
      <input type="range" min={min} max={max} value={value} onChange={(e) => onChange(Number(e.target.value))} className="pixel-range w-full" />
    </label>
  );
}

function Verdict({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-2 text-sm font-medium">
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-leaf" : "bg-koi"}`} />
      <span className={ok ? "text-leaf" : "text-koi"}>{children}</span>
    </p>
  );
}

export function PeopleScreenToy() {
  const [left, setLeft] = useState(14);
  const [tenure, setTenure] = useState(30);
  const [current, setCurrent] = useState(false);

  const rules: [string, boolean, string][] = [
    ["Not a current employee", !current, current ? "still lists the company as a current employer" : "no current role at the company"],
    ["Cooling-off", !current && left >= MIN_LEFT, left < MIN_LEFT ? `left ${left} months ago, less than ${MIN_LEFT}` : `left at least ${MIN_LEFT} months ago`],
    ["Freshness", left <= MAX_LEFT, left > MAX_LEFT ? `left ${left} months ago, more than ${MAX_LEFT}` : `within ${MAX_LEFT} months`],
    ["Minimum tenure", tenure >= MIN_TENURE, tenure < MIN_TENURE ? `${tenure} months there, below ${MIN_TENURE}` : `${tenure} months there`],
  ];
  const pass = rules.every(([, ok]) => ok);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Slider label="Left the company" value={left} min={0} max={36} unit="months ago" onChange={setLeft} />
        <Slider label="Time there" value={tenure} min={0} max={60} unit="months" onChange={setTenure} />
      </div>
      <button
        onClick={() => setCurrent((c) => !c)}
        className={`w-fit rounded-full border px-3 py-1 text-xs transition ${current ? "border-koi/60 text-koi" : "border-white/15 text-mist hover:text-cream"}`}
      >
        {current ? "✓ " : ""}Still works there
      </button>
      <ul className="flex flex-col divide-y divide-white/8 rounded-lg border border-white/8 text-sm">
        {rules.map(([name, ok, why]) => (
          <li key={name} className="flex items-baseline gap-3 px-3 py-2">
            <span className={ok ? "text-leaf" : "text-koi"}>{ok ? "✓" : "✗"}</span>
            <span className="text-cream">{name}</span>
            <span className="ml-auto text-right text-xs text-mist">{why}</span>
          </li>
        ))}
      </ul>
      <Verdict ok={pass}>{pass ? "Passes the people screen" : "Filtered out, with the reason shown"}</Verdict>
      <p className="text-xs text-mist">Same thresholds as the server&apos;s people screen (default settings).</p>
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
        className="w-full resize-none rounded-lg border border-white/10 bg-white/[.03] p-3 text-sm leading-relaxed text-cream outline-none focus:border-white/30"
        placeholder="Type an expert's answer"
      />
      <p className="min-h-[3.5rem] rounded-lg border border-white/8 bg-white/[.02] p-3 text-sm leading-relaxed text-mist">
        {parts.map((p, i) => p.hit
          ? <mark key={i} className="rounded bg-koi/20 px-0.5 text-koi">{p.t}</mark>
          : <span key={i}>{p.t}</span>)}
      </p>
      <Verdict ok={!hits.length}>
        {hits.length ? `Held for a person: ${hits.length} flagged phrase${hits.length > 1 ? "s" : ""}` : "Clear: passed on to the model screen"}
      </Verdict>
      <p className="text-xs text-mist">
        This runs only the code rule. On the server a model also reads every answer, and its quotes are checked in code.
      </p>
    </div>
  );
}
