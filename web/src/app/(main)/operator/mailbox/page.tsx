"use client";

// Operator-only: the invitations as they landed in the local Mailpit inbox (every one addressed to a teammate).
import { useCallback, useEffect, useState } from "react";
import { api, type MailItem, type MailMessage } from "@/lib/api";

export default function MailboxPage() {
  const [items, setItems] = useState<MailItem[] | null>(null);
  const [open, setOpen] = useState<MailMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.mailbox().then(setItems).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-[26px] font-semibold tracking-[-.02em]">Mailbox</h1>
        <p className="text-sm text-zinc-400">
          Every invitation the service sent, as delivered to the local inbox. All are addressed to teammates who answer as
          the expert; no email leaves the service. Open one and follow its private link to answer.
        </p>
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {items === null ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">No email yet.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
          <div className="flex flex-col overflow-hidden rounded-lg border border-zinc-800">
            {items.map((m, i) => (
              <button
                key={m.id}
                onClick={() => api.mailboxMessage(m.id).then(setOpen).catch((e) => setError(e.message))}
                className={`flex flex-col gap-0.5 px-3.5 py-2.5 text-left text-[13px] hover:bg-hover ${i ? "border-t border-zinc-800" : ""} ${open?.id === m.id ? "bg-hover" : ""}`}
              >
                <span className="font-medium">{m.subject}</span>
                <span className="text-xs text-zinc-500">to {m.to.join(", ")} · {new Date(m.created).toLocaleString()}</span>
              </button>
            ))}
          </div>
          <div className="rounded-lg border border-zinc-800 p-4 text-[13px]">
            {open ? (
              <div className="flex flex-col gap-2">
                <span className="text-[15px] font-semibold">{open.subject}</span>
                <span className="text-xs text-zinc-500">to {open.to.join(", ")}</span>
                <pre className="whitespace-pre-wrap font-sans leading-relaxed text-zinc-300">
                  {open.text.split(/(https?:\/\/\S+)/).map((part, i) =>
                    /^https?:\/\//.test(part) ? <a key={i} href={part} className="text-sky-300 underline">{part}</a> : part,
                  )}
                </pre>
              </div>
            ) : (
              <span className="text-zinc-500">Select an email.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
