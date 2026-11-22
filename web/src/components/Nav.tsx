"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function Nav() {
  const path = usePathname();
  const [pending, setPending] = useState(0);

  useEffect(() => {
    // held answers waiting for a team member
    // stops polling when the server asks for the operator key and none is saved in this browser
    const load = () =>
      api.operatorResponses({ status: "held" }).then((r) => setPending(r.length)).catch((e: Error) => {
        if (e.message.startsWith("401")) clearInterval(t);
      });
    const t = setInterval(load, 5000);
    load();
    return () => clearInterval(t);
  }, []);

  const color = (active: boolean) => (active ? "text-foreground" : "text-zinc-400 hover:text-foreground");

  return (
    <nav className="mx-auto flex max-w-[1100px] flex-wrap items-center gap-[22px] px-6 py-3 text-sm">
      <Link href="/" className="text-base font-semibold text-foreground">Synex</Link>
      <Link href="/ask" className={color(path === "/ask" || path.startsWith("/cases"))}>Ask</Link>
      <span className="ml-auto text-[11px] uppercase tracking-[.06em] text-zinc-500">Operator</span>
      <Link href="/operator/approvals" className={`flex items-center gap-1.5 ${color(path.startsWith("/operator/approvals"))}`}>
        Operator queue
        {pending > 0 && (
          <span className="rounded-full bg-amber-950 px-[7px] text-[11px] font-medium text-amber-300">{pending}</span>
        )}
      </Link>
      <Link href="/operator/mailbox" className={color(path.startsWith("/operator/mailbox"))}>Mailbox</Link>
      <Link href="/operator/audit" className={color(path.startsWith("/operator/audit"))}>Audit trail</Link>
    </nav>
  );
}
