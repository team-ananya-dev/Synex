import { Suspense } from "react";
import { Nav } from "@/components/Nav";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-zinc-800 bg-background/90 backdrop-blur">
        <Suspense fallback={<div className="h-[45px]" />}>
          <Nav />
        </Suspense>
      </header>
      <main className="mx-auto box-border w-full max-w-[1100px] flex-1 px-6 pt-9 pb-20">{children}</main>
      <footer className="border-t border-line px-6 py-3.5 text-center text-xs text-zinc-600">
        Every result comes from live Crustdata and Claude calls. No payments are made: prices are quotes only. Experts are teammates
        answering as personas; mail goes only to the teammate allowlist, through a local inbox.
      </footer>
    </div>
  );
}
