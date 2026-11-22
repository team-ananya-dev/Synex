"""Append-only, hash-chained audit events.

Each event stores the previous event's hash and its own. The hash covers the
previous hash plus the event's content, so editing any row breaks the chain.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

GENESIS = "0" * 64


def _digest(prev_hash: str, case_id: str | None, type_: str, payload: str, created_at: str) -> str:
    body = json.dumps([prev_hash, case_id, type_, payload, created_at], separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def append_event(conn: sqlite3.Connection, case_id: str | None, type_: str, payload: dict) -> int:
    payload_json = json.dumps(payload, sort_keys=True, default=str)
    created_at = datetime.now(timezone.utc).isoformat()
    # one writer at a time so the chain cannot fork
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else GENESIS
        digest = _digest(prev, case_id, type_, payload_json, created_at)
        cur = conn.execute(
            "INSERT INTO events (case_id, type, payload, created_at, prev_hash, hash) VALUES (?,?,?,?,?,?)",
            (case_id, type_, payload_json, created_at, prev, digest),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return cur.lastrowid


def verify_chain(conn: sqlite3.Connection) -> tuple[bool, int | None]:
    """Return (ok, first_bad_id)."""
    prev = GENESIS
    for r in conn.execute("SELECT * FROM events ORDER BY id"):
        if r["prev_hash"] != prev or r["hash"] != _digest(prev, r["case_id"], r["type"], r["payload"], r["created_at"]):
            return False, r["id"]
        prev = r["hash"]
    return True, None
