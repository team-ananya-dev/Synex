"use client";

// Operator pages show real people's names and full answers. On a hosted deployment the server asks for the
// operator key; it is entered once here and kept in this browser only.
import { useState, useSyncExternalStore } from "react";
import { operatorKey, setOperatorKey } from "@/lib/api";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  // read from this browser's storage; the server render sees no key
  const saved = useSyncExternalStore(() => () => {}, operatorKey, () => "");
  const [draft, setDraft] = useState("");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-zinc-800 px-3 py-2 text-xs text-zinc-400">
        <span>Operator area: real names and full answers. Team members only.</span>
        {saved ? (
          <span className="ml-auto flex items-center gap-2">
            operator key set
            <button onClick={() => { setOperatorKey(""); location.reload(); }} className="underline">clear</button>
          </span>
        ) : (
          <form
            className="ml-auto flex items-center gap-2"
            onSubmit={(e) => { e.preventDefault(); setOperatorKey(draft.trim()); location.reload(); }}
          >
            <input
              type="password"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="operator key (hosted only)"
              className="rounded border border-zinc-700 bg-background px-2 py-1"
            />
            <button type="submit" className="rounded border border-zinc-700 px-2 py-1">Save</button>
          </form>
        )}
      </div>
      {children}
    </div>
  );
}
