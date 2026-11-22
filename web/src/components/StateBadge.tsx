import type { CaseState } from "@/lib/api";

export const TONE = {
  zinc: "bg-zinc-800 text-zinc-300",
  sky: "bg-sky-950 text-sky-300",
  amber: "bg-amber-950 text-amber-300",
  violet: "bg-violet-950 text-violet-300",
  emerald: "bg-emerald-950 text-emerald-300",
  red: "bg-red-950 text-red-300",
} as const;

const STATE_TONE: Record<CaseState, keyof typeof TONE> = {
  DRAFT: "zinc",
  PLANNED: "sky",
  SOURCING: "sky",
  AWAITING_APPROVAL: "amber",
  COLLECTING: "violet",
  SYNTHESIZING: "violet",
  DELIVERED: "emerald",
  REFUSED: "red",
  FAILED: "red",
  LIMIT_REACHED: "amber",
};

export function Pill({ tone, children, className = "" }: { tone: keyof typeof TONE; children: React.ReactNode; className?: string }) {
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${TONE[tone]} ${className}`}>{children}</span>;
}

export function StateBadge({ state, wide = false }: { state: CaseState; wide?: boolean }) {
  return (
    <Pill tone={STATE_TONE[state] ?? "zinc"} className={wide ? "min-w-24 text-center" : ""}>
      {state.replace("_", " ").toLowerCase()}
    </Pill>
  );
}

export function SimulatedTag({ children = "simulated" }: { children?: React.ReactNode }) {
  return (
    <span className="rounded border border-[#4a3510] px-1.5 py-px font-mono text-[11px] text-amber-300">{children}</span>
  );
}
