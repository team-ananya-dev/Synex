"use client";

import { useEffect, useRef, useState } from "react";
import { eventsUrl, TERMINAL_STATES, type Audience, type CaseState, type SynexEvent } from "./api";

// Follows the case event stream (customer or operator). The server closes the
// stream at every job.paused (after planning, after outreach drafts); EventSource
// then reconnects with Last-Event-ID and picks up from there, so later events
// (plan.approved, sourcing, approval.*, mail.*) still arrive live.
// We close for good only on a terminal case state.
export function useCaseEvents(
  caseId: string | undefined,
  audience: Audience,
  onEvent?: (e: SynexEvent) => void,
) {
  // events are tagged with their case so a new case id starts from an empty list
  const [log, setLog] = useState<{ caseId?: string; events: SynexEvent[] }>({ events: [] });
  const [connected, setConnected] = useState(false);
  const handler = useRef(onEvent);

  useEffect(() => {
    handler.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!caseId) return;
    const seen = new Set<number>();
    const source = new EventSource(eventsUrl(caseId, audience));

    const receive = (msg: MessageEvent) => {
      const event = JSON.parse(msg.data) as SynexEvent;
      if (seen.has(event.id)) return;
      seen.add(event.id);
      setLog((prev) => ({ caseId, events: prev.caseId === caseId ? [...prev.events, event] : [event] }));
      handler.current?.(event);
      if (event.type === "case.state" && TERMINAL_STATES.includes(event.state as CaseState)) {
        source.close();
        setConnected(false);
      }
    };

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    // the server sends named events, so listen for each type, plus unnamed messages
    for (const type of KNOWN_TYPES) source.addEventListener(type, receive);
    source.onmessage = receive;
    return () => source.close();
  }, [caseId, audience]);

  return { events: log.caseId === caseId ? log.events : [], connected };
}

const KNOWN_TYPES = [
  "case.created", "case.state", "plan.approved", "stage.started", "stage.done", "stage.failed",
  "crustdata.call", "llm.call", "job.paused", "competitor.lookup_failed",
  "approval.requested", "approval.approved", "approval.rejected",
  "mail.sent", "mail.blocked", "mail.failed",
  "outreach.batch_approved",
  "response.received", "response.screened",
];
