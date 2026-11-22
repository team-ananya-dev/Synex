"""Audit trail and cost log. Read-only; nothing here can change a record."""
from fastapi import APIRouter, Query

from ..core import config, db, llm
from ..core.events import verify_chain
from . import views

router = APIRouter()


@router.get("/audit/events")
def audit_events(case_id: str | None = None, after: int = 0, limit: int = Query(200, ge=1, le=1000)):
    """The hash-chained event log, oldest first. Operator only: payloads can hold real people's details."""
    conn = db.connect()
    try:
        sql, args = "SELECT * FROM events WHERE id>?", [after]
        if case_id:
            sql += " AND case_id=?"; args.append(case_id)
        rows = conn.execute(sql + " ORDER BY id LIMIT ?", (*args, limit)).fetchall()
        import json
        return [{"id": r["id"], "case_id": r["case_id"], "type": r["type"], "payload": json.loads(r["payload"]),
                 "at": r["created_at"], "prev_hash": r["prev_hash"], "hash": r["hash"]} for r in rows]
    finally:
        conn.close()


@router.get("/audit/verify")
def audit_verify():
    """Recompute the whole hash chain. ok=false names the first event that was changed."""
    conn = db.connect()
    try:
        ok, bad = verify_chain(conn)
        n = conn.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
        return {"ok": ok, "first_bad_event_id": bad, "events_checked": n}
    finally:
        conn.close()


def _cost_rows(conn, where: str, args: tuple) -> dict:
    cd = [dict(r) for r in conn.execute(
        "SELECT call_id, case_id, purpose, endpoint, status, credits, latency_ms, cache_hit, error, created_at"
        f" FROM crustdata_calls WHERE {where} ORDER BY id", args)]
    lc = [dict(r) for r in conn.execute(
        "SELECT call_id, case_id, purpose, model, input_tokens, output_tokens, cost_usd, attempt, valid, error, created_at"
        f" FROM llm_calls WHERE {where} ORDER BY id", args)]
    return {"crustdata_calls": cd, "llm_calls": lc,
            "totals": {"crustdata_credits": round(sum(c["credits"] for c in cd), 4),
                       "model_usd": round(sum(c["cost_usd"] or 0 for c in lc), 6)}}


@router.get("/cases/{case_id}/costs")
def case_costs(case_id: str):
    """Every Crustdata and model call of one case with its cost. Prompts and responses are not included here."""
    conn = db.connect()
    try:
        return _cost_rows(conn, "case_id=?", (case_id,))
    finally:
        conn.close()


@router.get("/costs")
def total_costs():
    """Spend across all cases against the budget. Model budget is the model API budget for the running app."""
    conn = db.connect()
    try:
        out = _cost_rows(conn, "1=1", ())
        spent = out["totals"]["model_usd"]
        return {**out["totals"], "model_budget_usd": llm.BUDGET_USD, "model_remaining_usd": round(llm.BUDGET_USD - spent, 6),
                "demo_mode": config.demo_mode(), "crustdata_calls": len(out["crustdata_calls"]), "llm_calls": len(out["llm_calls"])}
    finally:
        conn.close()
