"""Case API: create a case, read it, and stream its events."""
import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..core import db
from . import runner

router = APIRouter()
TERMINAL_STATES = {"REFUSED", "FAILED"}


class NewCase(BaseModel):
    question: str = Field(min_length=5, max_length=2000)


def _case_view(conn, case_id: str) -> dict:
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        raise HTTPException(404, "no such case")
    stages = {}
    for r in conn.execute("SELECT stage, result FROM stage_results WHERE case_id=? ORDER BY id", (case_id,)):
        stages[r["stage"]] = json.loads(r["result"])
    credits = conn.execute("SELECT COALESCE(SUM(credits),0) c FROM crustdata_calls WHERE case_id=?", (case_id,)).fetchone()["c"]
    usd = conn.execute("SELECT COALESCE(SUM(cost_usd),0) c FROM llm_calls WHERE case_id=?", (case_id,)).fetchone()["c"]
    return {
        "id": case["id"], "question": case["question"], "state": case["state"], "refusal_reason": case["refusal_reason"],
        "created_at": case["created_at"], "stages": stages,
        "cost": {"crustdata_credits": credits, "model_usd": round(usd, 6), "credit_cap": runner.CREDIT_CAP},
    }


@router.post("/cases", status_code=201)
def create_case(body: NewCase, tasks: BackgroundTasks):
    conn = db.connect()
    case_id = runner.create_case(conn, body.question.strip())
    conn.close()
    tasks.add_task(runner.run_case, case_id)
    return {"id": case_id, "state": "DRAFT"}


@router.get("/cases")
def list_cases():
    conn = db.connect()
    rows = conn.execute("SELECT id, question, state, created_at FROM cases ORDER BY created_at DESC LIMIT 50").fetchall()
    return [dict(r) for r in rows]


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    conn = db.connect()
    try:
        return _case_view(conn, case_id)
    finally:
        conn.close()


@router.get("/cases/{case_id}/events")
async def stream_events(case_id: str, after: int = Query(0), last_event_id: int | None = Header(None)):
    """Server-sent events. Replays from `after` (or Last-Event-ID), then follows live until the job ends."""
    conn = db.connect()
    if not conn.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "no such case")
    cursor = last_event_id if last_event_id is not None else after

    async def gen():
        nonlocal cursor
        try:
            while True:
                rows = conn.execute("SELECT * FROM events WHERE case_id=? AND id>? ORDER BY id", (case_id, cursor)).fetchall()
                for r in rows:
                    cursor = r["id"]
                    payload = json.loads(r["payload"])
                    yield f"id: {r['id']}\nevent: {r['type']}\ndata: {json.dumps({'id': r['id'], 'type': r['type'], 'at': r['created_at'], **payload})}\n\n"
                    if r["type"] == "job.paused" or (r["type"] == "case.state" and payload.get("state") in TERMINAL_STATES):
                        return
                await asyncio.sleep(0.4)
        finally:
            conn.close()

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
