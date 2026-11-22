"""Screened responses: what the customer may read, and the team's review of held answers.

Customer route: only accepted answers, and redacted answers with the flagged spans removed, each under an
anonymous expert ref. Held and rejected answers appear only as counts. No names, links or addresses.
Operator routes: held answers with their full text, and the accept or reject click. Nobody edits an answer.
"""
import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..actions.mail import TEAM_MEMBERS
from ..core import db
from ..jobs.views import expert_ref
from ..stages import s7_response_screen as s7

router = APIRouter()
VERDICTS = ("accepted", "redacted", "held", "rejected")


def _rows(conn, case_id: str | None = None):
    """Each response with its latest screen (or none yet), oldest first."""
    sql = ("SELECT r.*, o.persona_title, o.persona_company, s.verdict, s.reason, s.redacted_text, s.flagged_spans,"
           " s.code_flags, s.decided_by, s.llm_call_id AS screen_call_id FROM responses r"
           " JOIN outreach o ON o.id = r.outreach_id"
           " LEFT JOIN response_screens s ON s.id = (SELECT MAX(id) FROM response_screens WHERE response_id = r.response_id)")
    args: tuple = ()
    if case_id:
        sql += " WHERE r.case_id = ?"
        args = (case_id,)
    return conn.execute(sql + " ORDER BY r.id", args).fetchall()


@router.get("/customer/cases/{case_id}/responses")
def customer_responses(case_id: str):
    conn = db.connect()
    try:
        if not conn.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
            raise HTTPException(404, "no such case")
        coverage: dict[str, dict[str, int]] = {}
        shown = []
        for r in _rows(conn, case_id):
            c = coverage.setdefault(str(r["subquestion_index"]), {"received": 0, "pending": 0, **{v: 0 for v in VERDICTS}})
            c["received"] += 1
            c[r["verdict"] or "pending"] += 1
            if r["verdict"] in ("accepted", "redacted"):
                shown.append({
                    "response_id": r["response_id"], "ref": expert_ref(case_id, r["person_id"]),
                    "role": r["persona_title"], "company": r["persona_company"],
                    "subquestion_index": r["subquestion_index"], "verdict": r["verdict"],
                    "text": r["text"] if r["verdict"] == "accepted" else r["redacted_text"],
                    "confidence": r["confidence"], "mode": r["mode"], "created_at": r["created_at"],
                })
        return {"coverage": coverage, "responses": shown}
    finally:
        conn.close()


@router.get("/operator/responses")
def operator_responses(status: str | None = Query(None), case_id: str | None = None):
    """Operator only: full answer text, the screen's reason and flags. status filters on the latest verdict."""
    conn = db.connect()
    try:
        out = []
        for r in _rows(conn, case_id):
            verdict = r["verdict"] or "pending"
            if status and verdict != status:
                continue
            out.append({
                "response_id": r["response_id"], "case_id": r["case_id"], "ref": expert_ref(r["case_id"], r["person_id"]),
                "persona_title": r["persona_title"], "persona_company": r["persona_company"],
                "subquestion_index": r["subquestion_index"], "kind": r["kind"], "text": r["text"],
                "confidence": r["confidence"], "mode": r["mode"], "verdict": verdict, "reason": r["reason"],
                "redacted_text": r["redacted_text"], "flagged_spans": json.loads(r["flagged_spans"] or "[]"),
                "code_flags": json.loads(r["code_flags"] or "[]"), "decided_by": r["decided_by"],
                "llm_call_id": r["screen_call_id"], "created_at": r["created_at"],
            })
        return out
    finally:
        conn.close()


class Review(BaseModel):
    approver: str
    decision: str  # accept | reject


@router.post("/operator/responses/{response_id}/decide")
def review_held(response_id: str, body: Review):
    """A team member's click on a held answer: accept it as written, or reject it. The text is never changed."""
    approver = body.approver.strip().lower()
    if approver not in TEAM_MEMBERS:
        raise HTTPException(403, f"{body.approver!r} is not a registered team member")
    if body.decision not in ("accept", "reject"):
        raise HTTPException(422, "decision must be accept or reject")
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM responses WHERE response_id=?", (response_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "no such response")
        current = s7.latest(conn, response_id)
        if current is None or current["verdict"] != "held":
            raise HTTPException(409, f"only a held response can be reviewed; this one is {current['verdict'] if current else 'not screened yet'}")
        verdict = "accepted" if body.decision == "accept" else "rejected"
        s7.record(conn, row, {
            "verdict": verdict, "reason": f"held response {verdict} by {approver} after review",
            "redacted_text": None, "flagged_spans": [], "code_flags": json.loads(current["code_flags"]), "llm_call_id": None,
        }, approver)
        return {"response_id": response_id, "verdict": verdict, "decided_by": approver}
    finally:
        conn.close()
