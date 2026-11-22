import { Suspense } from "react";
import { CaseView } from "./CaseView";

// The case id is only known at request time, so the client view sits in Suspense
// (required with cacheComponents; see node_modules/next/dist/docs, useParams).
export default function CasePage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading case…</p>}>
      <CaseView />
    </Suspense>
  );
}
