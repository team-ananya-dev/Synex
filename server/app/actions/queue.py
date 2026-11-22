"""Approval queue for outreach. Nothing is sent until a registered team member approves."""
import hashlib
import json
import re
import secrets
import time
import sqlite3
from datetime import datetime, timezone

import httpx

from ..core import config
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
    if approver.lower() not in mail.APPROVERS:
        raise QueueError(403, f"{approver!r} is not a registered approver")
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


def action_key(case_id: str, action_type: str, target_id) -> str:
    return hashlib.sha256(f"{case_id}|{action_type}|{target_id}".encode()).hexdigest()


def _in_mailbox(key: str) -> bool | None:
    """Is a message with this key's Message-ID already in the mailbox? None if the mailbox cannot be read."""
    try:
        r = httpx.get(f"{config.mailpit_api()}/api/v1/messages?limit=1000", timeout=10)
        r.raise_for_status()
        return any((m.get("MessageID") or "").strip("<>") == f"{key}@synex.local" for m in r.json().get("messages", []))
    except httpx.HTTPError:
        return None


def _send(conn: sqlite3.Connection, row: sqlite3.Row, by: str) -> dict:
    """Send one approved invitation exactly once, through the allowlist gate. A blocked or failed send is recorded,
    never retried silently."""
    outreach_id, case_id = row["id"], row["case_id"]
    key = action_key(case_id, "send_invitation", outreach_id)
    act = conn.execute("SELECT * FROM actions WHERE key=?", (key,)).fetchone()
    if act and act["status"] == "DONE":                       # already sent: never again
        if row["status"] != "SENT":
            _set(conn, outreach_id, "SENT", sent_at=_now())
        return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())
    if act and act["status"] == "PENDING":                    # the process died during this send
        found = _in_mailbox(key)
        if found:
            conn.execute("UPDATE actions SET status='DONE', response=?, updated_at=? WHERE key=?",
                         ("found in the mailbox after a restart; not sent again", _now(), key))
            _set(conn, outreach_id, "SENT", sent_at=_now())
            append_event(conn, case_id, "mail.sent", {"outreach_id": outreach_id, "to": row["to_address"], "recovered": True})
            return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())
        if found is None:                                      # cannot tell: never risk a second email
            conn.execute("UPDATE actions SET status='UNVERIFIED', updated_at=? WHERE key=?", (_now(), key))
            reason = "the process stopped during this send and the mailbox could not be checked; not sent again"
            _set(conn, outreach_id, "FAILED", block_reason=reason)
            append_event(conn, case_id, "mail.failed", {"outreach_id": outreach_id, "error": reason})
            return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())
    else:
        conn.execute("INSERT INTO actions (key, case_id, action_type, target_id, status, created_at, updated_at)"
                     " VALUES (?,?,?,?,?,?,?)", (key, case_id, "send_invitation", str(outreach_id), "PENDING", _now(), _now()))
        conn.commit()
    headers = {"X-Synex-Case": case_id, "X-Synex-Persona": f"{row['persona_title']} ({row['persona_company']})",
               "Message-ID": f"<{key}@synex.local>"}
    try:
        mail.send_mail(row["to_address"], row["subject"], row["body"], headers)
    except mail.MailBlocked as e:
        conn.execute("UPDATE actions SET status='DONE', response=?, updated_at=? WHERE key=?", (f"blocked: {e}", _now(), key))
        _set(conn, outreach_id, "BLOCKED", block_reason=str(e))
        append_event(conn, case_id, "mail.blocked", {"outreach_id": outreach_id, "reason": str(e)})
    except Exception as e:  # SMTP down, refused, timed out: nothing was accepted, so the action is not done
        conn.execute("DELETE FROM actions WHERE key=?", (key,))
        _set(conn, outreach_id, "FAILED", block_reason=f"{type(e).__name__}: {e}")
        append_event(conn, case_id, "mail.failed", {"outreach_id": outreach_id, "error": f"{type(e).__name__}: {e}"})
    else:
        conn.execute("UPDATE actions SET status='DONE', response=?, updated_at=? WHERE key=?", ("accepted by the mail server", _now(), key))
        _set(conn, outreach_id, "SENT", sent_at=_now())
        append_event(conn, case_id, "mail.sent", {"outreach_id": outreach_id, "to": row["to_address"]})
    conn.commit()
    return view(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())


def _mark_approved(conn, row: sqlite3.Row, by: str) -> None:
    _set(conn, row["id"], "APPROVED", decided_by=by, decided_at=_now())
    append_event(conn, row["case_id"], "approval.approved", {"outreach_id": row["id"], "by": by})


def resume_sends(conn: sqlite3.Connection) -> list[str]:
    """At startup: finish every invitation that was approved but not yet sent. Returns the case ids touched."""
    rows = list(conn.execute("SELECT * FROM outreach WHERE status='APPROVED' ORDER BY id"))
    for r in rows:
        _send(conn, r, r["decided_by"] or "customer")
    return sorted({r["case_id"] for r in rows})


def approve(conn: sqlite3.Connection, outreach_id: int, approver: str) -> dict:
    row = _get(conn, outreach_id, approver)
    _mark_approved(conn, row, approver.lower())
    return _send(conn, conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone(), approver.lower())


def anonymised_body(row: sqlite3.Row) -> str:
    """The invitation as the customer may see it: no first name, no private link."""
    body = re.sub(rf"https?://\S*{re.escape(row['token'])}\S*", "[private link]", row["body"])
    for part in (row["name"] or "").split():
        if len(part.strip(" .")) > 1:
            body = re.sub(rf"\b{re.escape(part.strip(' .'))}\b", "[first name]", body, flags=re.I)
    return body


def invites(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    """What the customer reviews before anything is sent. Never carries a name, a link or an address."""
    from ..jobs.views import expert_ref  # imported here: views does not import this module, but routes import both
    out = []
    for r in conn.execute("SELECT * FROM outreach WHERE case_id=? ORDER BY id", (case_id,)):
        flags = json.loads(r["flags"])
        out.append({"ref": expert_ref(case_id, r["person_id"]), "role": r["persona_title"], "company": r["persona_company"],
                    "tenure_months": r["tenure_months"], "subquestion_indices": json.loads(r["subquestion_indices"]),
                    "subject": r["subject"], "preview": anonymised_body(r), "status": r["status"],
                    "flagged": bool(flags), "flag_reasons": [f["reason"] for f in flags],
                    "selected_by_default": r["status"] == "DRAFTED" and not flags})
    return out


def approve_batch(conn: sqlite3.Connection, case_id: str, refs: list[str], by: str = "customer") -> dict:
    """The customer's click. The listed experts are invited; every other waiting draft is dropped. Each email is its
    own logged approval, and each is sent through the allowlist gate."""
    from ..jobs.views import expert_ref
    if by.lower() not in mail.APPROVERS:
        raise QueueError(403, f"{by!r} is not a registered approver")
    waiting = list(conn.execute("SELECT * FROM outreach WHERE case_id=? AND status='DRAFTED' ORDER BY id", (case_id,)))
    by_ref = {expert_ref(case_id, r["person_id"]): r for r in waiting}
    unknown = [x for x in refs if x not in by_ref]
    if not refs or unknown:
        raise QueueError(422, "choose at least one expert" if not refs else f"not waiting for approval in this case: {unknown}")
    chosen = {by_ref[x]["id"] for x in refs}
    result = {"sent": 0, "dropped": 0, "blocked": 0, "failed": 0}
    # record every decision first, so a crash part-way through still knows what the customer approved
    for r in waiting:
        if r["id"] in chosen:
            _mark_approved(conn, r, by.lower())
        else:
            _set(conn, r["id"], "REJECTED", decided_by=by.lower(), decided_at=_now(), block_reason="dropped by the customer")
            append_event(conn, case_id, "approval.rejected", {"outreach_id": r["id"], "by": by.lower()})
            result["dropped"] += 1
    delay = config.send_delay_seconds()
    for oid in sorted(chosen):
        status = _send(conn, conn.execute("SELECT * FROM outreach WHERE id=?", (oid,)).fetchone(), by.lower())["status"]
        result[{"SENT": "sent", "BLOCKED": "blocked", "FAILED": "failed"}[status]] += 1
        if delay:
            time.sleep(delay)
    append_event(conn, case_id, "outreach.batch_approved", {**result, "by": by.lower()})
    return result


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
