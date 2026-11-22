"""Expert page API. One private link (token) per approved outreach email.

A teammate opens the link and answers in the persona of that candidate. The page shows the persona's role,
the sub-questions and the ground rules; it never shows the customer, other experts or anyone's contact
details. Answers are stored append-only and each gets a response_id the memo can cite.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, model_validator

from ..actions.ledger import CURRENCY
from ..actions.queue import expert_context
from ..core import db
from ..core.events import append_event
from ..jobs import runner
from ..stages import s7_response_screen
from .responses import router as responses_router

router = APIRouter()
router.include_router(responses_router)  # screened responses ride on this router, so main.py needs no change

# Simulated payout shown to the expert. A policy setting, not a result; no money moves.
PAYOUT_PER_ACCEPTED_ANSWER = float(os.environ.get("SYNEX_EXPERT_PAYOUT", "50"))

ATTESTATIONS = ("not_current_employee", "left_as_shown", "no_blocking_confidentiality", "no_confidential_info")


class Answer(BaseModel):
    index: int
    kind: Literal["answer", "dont_know", "confidential"]
    text: str = Field(default="", max_length=6000)
    confidence: Literal["low", "medium", "high"] | None = None

    @model_validator(mode="after")
    def text_only_for_answers(self):
        if self.kind == "answer":
            if len(self.text.strip()) < 2:
                raise ValueError(f"sub-question {self.index}: write an answer or pick 'I don't know'")
            if self.confidence is None:
                raise ValueError(f"sub-question {self.index}: rate your confidence")
        else:
            self.text, self.confidence = "", None
        return self


class Submission(BaseModel):
    mode: Literal["form", "voice", "text"] = "form"
    attestations: dict[str, bool]
    answers: list[Answer] = Field(min_length=1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _context_or_404(conn, token: str) -> dict:
    ctx = expert_context(conn, token)
    if ctx is None:
        raise HTTPException(404, "this link is not valid")
    return ctx


def _persona(conn, outreach_id: int) -> dict:
    row = conn.execute("SELECT persona_title, persona_company, tenure_months FROM outreach WHERE id=?",
                       (outreach_id,)).fetchone()
    return {"role": row["persona_title"], "company": row["persona_company"], "tenure_months": row["tenure_months"]}


def _answered(conn, outreach_id: int) -> set[int]:
    return {r["subquestion_index"] for r in conn.execute(
        "SELECT subquestion_index FROM responses WHERE outreach_id=?", (outreach_id,))}


@router.get("/expert/{token}")
def get_expert_page(token: str):
    """What the expert page shows. Only a link whose email was approved and sent is open."""
    conn = db.connect()
    try:
        ctx = _context_or_404(conn, token)
        if ctx["status"] != "SENT":
            return {"available": False, "reason": "This invitation is not active."}
        return {
            "available": True,
            "first_name": ctx["first_name"],
            "persona": _persona(conn, ctx["outreach_id"]),
            "subquestions": ctx["subquestions"],
            "submitted": bool(_answered(conn, ctx["outreach_id"])),
            "payout": {"per_accepted_answer": PAYOUT_PER_ACCEPTED_ANSWER, "currency": CURRENCY, "terms": "payout terms shown for illustration; no payment is made in this build"},
        }
    finally:
        conn.close()


@router.post("/expert/{token}/responses", status_code=201)
def submit_responses(token: str, body: Submission, tasks: BackgroundTasks):
    conn = db.connect()
    try:
        ctx = _context_or_404(conn, token)
        if ctx["status"] != "SENT":
            raise HTTPException(409, "this invitation is not active")
        if _answered(conn, ctx["outreach_id"]):
            raise HTTPException(409, "answers for this invitation were already submitted")
        missing = [a for a in ATTESTATIONS if not body.attestations.get(a)]
        if missing:
            raise HTTPException(422, f"confirm every statement before submitting: {', '.join(missing)}")
        wanted = sorted(s["index"] for s in ctx["subquestions"])
        got = sorted(a.index for a in body.answers)
        if got != wanted:
            raise HTTPException(422, f"answer each sub-question exactly once: expected {wanted}, got {got}")

        attest = json.dumps({a: True for a in ATTESTATIONS})
        created = []
        for a in sorted(body.answers, key=lambda a: a.index):
            rid = "R" + uuid.uuid4().hex[:8]
            conn.execute(
                "INSERT INTO responses (response_id, case_id, outreach_id, person_id, subquestion_index, mode, kind,"
                " text, confidence, attestations, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid, ctx["case_id"], ctx["outreach_id"], ctx["person_id"], a.index, body.mode, a.kind,
                 a.text.strip(), a.confidence, attest, _now()))
            created.append({"response_id": rid, "subquestion_index": a.index, "kind": a.kind})
        conn.commit()

        # events carry no answer text and no personal data, so the customer stream can pass them through
        for c in created:
            append_event(conn, ctx["case_id"], "response.received", {**c, "mode": body.mode})
        state = conn.execute("SELECT state FROM cases WHERE id=?", (ctx["case_id"],)).fetchone()["state"]
        if state == "AWAITING_APPROVAL":
            runner.set_state(conn, ctx["case_id"], "COLLECTING")
        tasks.add_task(s7_response_screen.screen_responses, [c["response_id"] for c in created])  # stage 7
        return {"received": created}
    finally:
        conn.close()
