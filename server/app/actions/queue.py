"""Approval queue for outreach. Nothing is sent until a registered team member approves."""
import json
import secrets
import sqlite3
from datetime import datetime, timezone

from ..core.events import append_event
from . import mail


class QueueError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_draft(conn: sqlite3.Connection, *, case_id: str, person_id: int, name: str | None, persona_title: str | None,
                 persona_company: str | None, tenure_months: int | None, subquestion_indices: list[int], flags: list[dict],
                 to_address: str, subject: str, body_template: str, link_base: str, llm_call_id: str | None) -> int:
    """Store a draft. {{link}} in the template becomes the expert's private link; {{first_name}} their first name."""
    token = secrets.token_urlsafe(16)
    first = (name or "").split(" ")[0].strip(" .").title()
    body = body_template.replace("{{first_name}}", first if len(first) > 1 else "there").replace("{{link}}", f"{link_base}/expert/{token}")
    cur = conn.execute(
        "INSERT INTO outreach (case_id, person_id, name, persona_title, persona_company, tenure_months, subquestion_indices, flags,"
        " token, to_address, subject, body, status, llm_call_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (case_id, person_id, name, persona_title, persona_company, tenure_months, json.dumps(subquestion_indices), json.dumps(flags),
         token, to_address, subject, body, "DRAFTED", llm_call_id, _now()))
    conn.commit()
    append_event(conn, case_id, "approval.requested", {
        "outreach_id": cur.lastrowid, "person_id": person_id, "persona": f"{persona_title} ({persona_company})",
        "subquestion_indices": subquestion_indices, "flagged": bool(flags)})
    return cur.lastrowid


def view(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["subquestion_indices"] = json.loads(d["subquestion_indices"])
    d["flags"] = json.loads(d["flags"])
    d.pop("token")  # the private link is already in the body; the bare token is not needed by the operator
    return d


def list_items(conn: sqlite3.Connection, status: str | None = None, case_id: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM outreach WHERE 1=1", []
    if status:
        sql += " AND status=?"; args.append(status)
    if case_id:
        sql += " AND case_id=?"; args.append(case_id)
    return [view(r) for r in conn.execute(sql + " ORDER BY id", args)]


def _get(conn, outreach_id: int, approver: str) -> sqlite3.Row:
    if approver.lower() not in mail.TEAM_MEMBERS:
        raise QueueError(403, f"{approver!r} is not a registered team member")
    row = conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone()
    if not row:
        raise QueueError(404, "no such draft")
    if row["status"] != "DRAFTED":
        raise QueueError(409, f"draft is already {row['status']}")
    return row


def _set(conn, outreach_id: int, status: str, **cols) -> None:
    sets = ", ".join(f"{k}=?" for k in cols)
    conn.execute(f"UPDATE outreach SET status=?, {sets} WHERE id=?", (status, *cols.values(), outreach_id))
    conn.commit()


def reject(conn: sqlite3.Connection, outreach_id: int, approver: str) -> dict:
    row = _get(conn, outreach_id, approver)
    _set(conn, outreach_id, "REJECTED", decided_by=approver.lower(), decided_at=_now())
    append_event(conn, row["case_id"], "approval.rejected", {"outreach_id": outreach_id, "by": approver.lower()})
    return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())


def approve(conn: sqlite3.Connection, outreach_id: int, approver: str) -> dict:
    """The human click. Sends through the allowlist gate; a blocked or failed send is recorded, never retried silently."""
    row = _get(conn, outreach_id, approver)
    by = approver.lower()
    append_event(conn, row["case_id"], "approval.approved", {"outreach_id": outreach_id, "by": by})
    headers = {"X-Synex-Case": row["case_id"], "X-Synex-Persona": f"{row['persona_title']} ({row['persona_company']})"}
    try:
        mail.send_mail(row["to_address"], row["subject"], row["body"], headers)
    except mail.MailBlocked as e:
        _set(conn, outreach_id, "BLOCKED", decided_by=by, decided_at=_now(), block_reason=str(e))
        append_event(conn, row["case_id"], "mail.blocked", {"outreach_id": outreach_id, "reason": str(e)})
    except Exception as e:  # SMTP down, refused, timed out
        _set(conn, outreach_id, "FAILED", decided_by=by, decided_at=_now(), block_reason=f"{type(e).__name__}: {e}")
        append_event(conn, row["case_id"], "mail.failed", {"outreach_id": outreach_id, "error": f"{type(e).__name__}: {e}"})
    else:
        _set(conn, outreach_id, "SENT", decided_by=by, decided_at=_now(), sent_at=_now())
        append_event(conn, row["case_id"], "mail.sent", {"outreach_id": outreach_id, "to": row["to_address"]})
    return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())


def expert_context(conn: sqlite3.Connection, token: str) -> dict | None:
    """What the expert page may show for a private link, or None for an unknown token. The page should only
    accept a link whose status is SENT. It carries no customer information and no other expert's data."""
    row = conn.execute("SELECT * FROM outreach WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    plan = conn.execute("SELECT result FROM stage_results WHERE case_id=? AND stage='s2_decomposer' ORDER BY id DESC LIMIT 1",
                        (row["case_id"],)).fetchone()
    subs = {s["index"]: s["text"] for s in json.loads(plan["result"])} if plan else {}
    first = (row["name"] or "").split(" ")[0].strip(" .").title()
    return {"outreach_id": row["id"], "case_id": row["case_id"], "person_id": row["person_id"],
            "first_name": first if len(first) > 1 else None, "status": row["status"],
            "subquestions": [{"index": i, "text": subs.get(i)} for i in json.loads(row["subquestion_indices"])]}
