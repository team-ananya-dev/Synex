import { Suspense } from "react";
import { ExpertView } from "./ExpertView";

// The token is only known at request time, so the client view sits in Suspense (cacheComponents).
export default function ExpertPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading…</p>}>
      <ExpertView />
    </Suspense>
  );
}
