"use client";

import { useEffect, useRef, useState } from "react";
import { eventsUrl, TERMINAL_STATES, type CaseState, type SynexEvent } from "./api";

// Follows GET /cases/{id}/events. The server closes the stream at job.paused;
// EventSource then reconnects with Last-Event-ID, and the server keeps that
// second stream open, so approval.* and mail.* events still arrive live.
// We close for good only on a terminal case state.
export function useCaseEvents(caseId: string | undefined, onEvent?: (e: SynexEvent) => void) {
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
    const source = new EventSource(eventsUrl(caseId));

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
  }, [caseId]);

  return { events: log.caseId === caseId ? log.events : [], connected };
}

const KNOWN_TYPES = [
  "case.created", "case.state", "stage.started", "stage.done", "stage.failed",
  "crustdata.call", "llm.call", "job.paused", "competitor.lookup_failed",
  "approval.requested", "approval.approved", "approval.rejected",
  "mail.sent", "mail.blocked", "mail.failed",
];
