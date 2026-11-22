import type { CaseState } from "@/lib/api";

const COLORS: Record<CaseState, string> = {
  DRAFT: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  PLANNED: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  SOURCING: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  AWAITING_APPROVAL: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  COLLECTING: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  SYNTHESIZING: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  DELIVERED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  REFUSED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

export function StateBadge({ state }: { state: CaseState }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${COLORS[state] ?? COLORS.DRAFT}`}>
      {state.replace("_", " ").toLowerCase()}
    </span>
  );
}
