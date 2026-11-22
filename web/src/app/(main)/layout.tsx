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
    </div>
  );
}
