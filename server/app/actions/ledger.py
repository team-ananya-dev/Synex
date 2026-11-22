"""Simulated ledger: holds, captures and releases. Append-only; every entry is also an audit event."""
import sqlite3
from datetime import datetime, timezone

from ..core import config
from ..core.events import append_event

CURRENCY = "USD (simulated)"


class LedgerError(Exception):
    pass


def quote(n_subquestions: int) -> dict:
    price = config.price_per_subquestion()
    return {"subquestions": n_subquestions, "price_per_subquestion": price, "hold_amount": round(n_subquestions * price, 2),
            "currency": CURRENCY}


def _add(conn, case_id: str, kind: str, amount: float, ref: str | None, note: str, by: str) -> int:
    cur = conn.execute(
        "INSERT INTO ledger (case_id, kind, amount, currency, ref, note, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (case_id, kind, round(amount, 2), CURRENCY, ref, note, by, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    append_event(conn, case_id, f"ledger.{kind.lower()}", {"amount": round(amount, 2), "currency": CURRENCY, "ref": ref, "by": by})
    return cur.lastrowid


def balance(conn: sqlite3.Connection, case_id: str) -> dict:
    sums = {k: 0.0 for k in ("HOLD", "CAPTURE", "RELEASE")}
    for r in conn.execute("SELECT kind, SUM(amount) a FROM ledger WHERE case_id=? GROUP BY kind", (case_id,)):
        sums[r["kind"]] = r["a"]
    return {"held": sums["HOLD"], "captured": sums["CAPTURE"], "released": sums["RELEASE"],
            "remaining": round(sums["HOLD"] - sums["CAPTURE"] - sums["RELEASE"], 2), "currency": CURRENCY}


def entries(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT kind, amount, currency, ref, note, created_by, created_at FROM ledger WHERE case_id=? ORDER BY id", (case_id,))]


def place_hold(conn, case_id: str, amount: float, by: str) -> int:
    if balance(conn, case_id)["held"] > 0:
        raise LedgerError("a hold is already placed for this case")
    return _add(conn, case_id, "HOLD", amount, None, "hold placed when the plan was approved", by)


def capture(conn, case_id: str, subquestion_index: int, amount: float, by: str) -> int:
    """Charge for one answered sub-question, never more than what is still held."""
    if amount > balance(conn, case_id)["remaining"]:
        raise LedgerError("capture is larger than the remaining hold")
    return _add(conn, case_id, "CAPTURE", amount, f"subquestion:{subquestion_index}", "sub-question answered", by)


def release_remaining(conn, case_id: str, by: str) -> int | None:
    left = balance(conn, case_id)["remaining"]
    return _add(conn, case_id, "RELEASE", left, None, "unused hold released at close", by) if left > 0 else None
