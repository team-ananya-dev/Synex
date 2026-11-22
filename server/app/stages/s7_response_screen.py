"""Stage 7: screen each expert answer before anyone sees it.

Verdicts: accepted (goes to the customer and the memo), redacted (goes in with the flagged spans removed),
held (waits for a team member to accept or reject), rejected (excluded, reason logged).

The small model proposes a verdict and quotes the spans it would remove. Code then checks it:
  - every flagged span must be an exact quote from the answer, or the reply is sent back once;
  - a redaction needs at least one verified span;
  - a code rule looks for leak phrases ("confidential", "internal deck", "I shouldn't say"...). If it finds
    one and the model said accepted, the answer is held for a person instead;
  - if the model's reply cannot be verified at all, the answer is held, never accepted.
Answers marked "I don't know" or "can't answer without confidential information" need no model call:
they are recorded as rejected (no answer to use) with that reason.
"""
import json
import re
from datetime import datetime, timezone

from ..core import db, llm
from ..core.events import append_event

RISK = re.compile(
    r"\b(confidential|nda|non[- ]disclosure|internal (?:document|deck|memo|report|dashboard|email|data|numbers)s?"
    r"|not (?:yet )?public|unreleased|unannounced|shouldn'?t (?:say|tell|share)|off the record|insider)\b", re.I)

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["accepted", "redacted", "held", "rejected"]},
        "reason": {"type": "string"},
        "flagged_spans": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "reason", "flagged_spans"],
}

SYSTEM = (
    "You screen one answer from a former employee before an expert-network customer sees it. Look for: non-public "
    "specifics (unreleased or internal figures, named customers' contract terms, internal documents, unannounced "
    "products), phrases that signal a leak (for example 'I shouldn't say, but'), pasted company material, and personal "
    "data about third parties. General first-hand experience, public facts, ranges and trends are fine.\n"
    "ACCEPTED: nothing problematic. REDACTED: mostly fine, but specific spans must be removed; quote each span exactly, "
    "copied character for character from the answer, in flagged_spans. HELD: you are unsure and a person should decide. "
    "REJECTED: the answer is mainly confidential or non-public material, or is not an answer to the question. "
    "Give a one-sentence reason that does not repeat any confidential content. flagged_spans is empty unless REDACTED."
)

NO_ANSWER = {
    "dont_know": "no answer given: the expert said they do not know",
    "confidential": "no answer given: the expert said they cannot answer without confidential information",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def validate(text: str, reply: dict) -> None:
    if not reply["reason"].strip():
        raise ValueError("give a reason")
    spans = [s for s in reply["flagged_spans"] if s.strip()]
    missing = [s for s in spans if _norm(s) not in _norm(text)]
    if missing:
        raise ValueError(f"flagged_spans must be exact quotes from the answer; not found: {missing[:3]}")
    if reply["verdict"] == "redacted" and not spans:
        raise ValueError("a redaction needs at least one flagged span")


def redact(text: str, spans: list[str]) -> str:
    """Replace each flagged span with [redacted]. Whitespace inside a span may differ from the answer."""
    out = text
    for span in sorted({s.strip() for s in spans if s.strip()}, key=len, reverse=True):
        pattern = r"\s+".join(re.escape(w) for w in span.split())
        out = re.sub(pattern, "[redacted]", out, flags=re.I)
    return out


def _context(conn, row) -> tuple[str, str]:
    plan = conn.execute("SELECT result FROM stage_results WHERE case_id=? AND stage='s2_decomposer' ORDER BY id DESC LIMIT 1",
                        (row["case_id"],)).fetchone()
    subs = {s["index"]: s["text"] for s in json.loads(plan["result"])} if plan else {}
    persona = conn.execute("SELECT persona_title FROM outreach WHERE id=?", (row["outreach_id"],)).fetchone()
    return subs.get(row["subquestion_index"], ""), (persona["persona_title"] if persona else None) or "former employee"


def decide(conn, row) -> dict:
    """Return the screening decision for one response row (not yet stored)."""
    if row["kind"] != "answer":
        return {"verdict": "rejected", "reason": NO_ANSWER[row["kind"]], "redacted_text": None, "flagged_spans": [],
                "code_flags": [], "llm_call_id": None}
    text = row["text"]
    hits = sorted({m.group(0).lower() for m in RISK.finditer(text)})
    question, role = _context(conn, row)
    try:
        reply, call_id = llm.call_json(
            conn, purpose="screen_response", case_id=row["case_id"], schema=SCHEMA, system=SYSTEM,
            user=f"Sub-question: {question}\nExpert's former role: {role}\nAnswer:\n{text}",
            validate=lambda r: validate(text, r),
        )
    except llm.InvalidModelReply as e:
        return {"verdict": "held", "reason": f"the screen's reply could not be verified ({e}); held for a team member",
                "redacted_text": None, "flagged_spans": [], "code_flags": hits, "llm_call_id": None}

    verdict, reason = reply["verdict"], reply["reason"].strip()
    spans = [s.strip() for s in reply["flagged_spans"] if s.strip()] if verdict == "redacted" else []
    if verdict == "accepted" and hits:
        verdict = "held"
        reason = f"{reason} Held by the code rule: the answer contains {', '.join(repr(h) for h in hits)}."
    return {"verdict": verdict, "reason": reason, "redacted_text": redact(text, spans) if verdict == "redacted" else None,
            "flagged_spans": spans, "code_flags": hits, "llm_call_id": call_id}


def record(conn, row, d: dict, decided_by: str) -> None:
    conn.execute(
        "INSERT INTO response_screens (response_id, verdict, reason, redacted_text, flagged_spans, code_flags, llm_call_id,"
        " decided_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (row["response_id"], d["verdict"], d["reason"], d["redacted_text"], json.dumps(d["flagged_spans"]),
         json.dumps(d["code_flags"]), d["llm_call_id"], decided_by, _now()))
    conn.commit()
    # no answer text and no reason in the event: the customer stream passes it through unchanged
    append_event(conn, row["case_id"], "response.screened", {
        "response_id": row["response_id"], "subquestion_index": row["subquestion_index"], "verdict": d["verdict"],
        "by": decided_by})


def screen_responses(response_ids: list[str]) -> None:
    """Background job after an expert submits. A failure holds the answer for a person; it is never accepted."""
    conn = db.connect()
    try:
        for rid in response_ids:
            row = conn.execute("SELECT * FROM responses WHERE response_id=?", (rid,)).fetchone()
            if row is None or latest(conn, rid) is not None:  # already screened: no second model call, no second event
                continue
            try:
                d = decide(conn, row)
            except Exception as e:  # budget reached, network error: a person decides instead
                d = {"verdict": "held", "reason": f"the screen failed ({type(e).__name__}); held for a team member",
                     "redacted_text": None, "flagged_spans": [], "code_flags": [], "llm_call_id": None}
            record(conn, row, d, "screen")
    finally:
        conn.close()


def sweep_unscreened() -> int:
    """After a restart: screen every response that has no screen row (its background job died with the server)."""
    conn = db.connect()
    try:
        ids = [r["response_id"] for r in conn.execute(
            "SELECT response_id FROM responses WHERE response_id NOT IN (SELECT response_id FROM response_screens) ORDER BY id")]
    finally:
        conn.close()
    if ids:
        screen_responses(ids)
    return len(ids)


def latest(conn, response_id: str):
    return conn.execute("SELECT * FROM response_screens WHERE response_id=? ORDER BY id DESC LIMIT 1", (response_id,)).fetchone()
