"""Case API. Operator routes show real people's details; /customer routes never do."""
import asyncio
import json
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..actions import pricing, queue
from ..core import config, db
from ..core.events import append_event
from . import runner, views

router = APIRouter()
TERMINAL_STATES = {"REFUSED", "FAILED"}


class NewCase(BaseModel):
    question: str = Field(min_length=5, max_length=2000)


class PlanApproval(BaseModel):
    panel_size: int = Field(ge=1, le=5)   # experts to contact per sub-question


def _read(fn, *args):
    conn = db.connect()
    try:
        return fn(conn, *args)
    finally:
        conn.close()


@router.post("/cases", status_code=201)
def create_case(body: NewCase, tasks: BackgroundTasks):
    conn = db.connect()
    case_id = runner.create_case(conn, body.question.strip())
    conn.close()
    tasks.add_task(runner.run_case, case_id)
    return {"id": case_id, "state": "DRAFT"}


@router.get("/cases")
def list_cases():
    return _read(lambda c: [dict(r) for r in c.execute(
        "SELECT id, question, state, created_at FROM cases ORDER BY created_at DESC LIMIT 50")])


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    return _read(views.operator_view, case_id)


@router.get("/customer/cases")
def list_customer_cases():
    return list_cases()


@router.get("/customer/cases/{case_id}")
def get_customer_case(case_id: str):
    return _read(views.customer_view, case_id)


@router.post("/customer/cases/{case_id}/approve-plan")
def approve_plan(case_id: str, body: PlanApproval, tasks: BackgroundTasks):
    """The customer's click: approves the plan and the panel size. Sourcing starts only after this, so no Crustdata
    credit is spent before the customer agrees. The quoted price is shown for information; no payment is taken."""
    conn = db.connect()
    try:
        case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(404, "no such case")
        if case["state"] != "PLANNED":
            raise HTTPException(409, f"the case is {case['state']}, not waiting for plan approval")
        plan = json.loads(conn.execute("SELECT result FROM stage_results WHERE case_id=? AND stage='s2_decomposer'"
                                       " ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()["result"])
        limit = config.dev_max_subquestions()
        quote = pricing.quote(len(plan if limit is None else plan[:limit]))
        params = {**json.loads(case["params"]), "panel_size": body.panel_size}
        conn.execute("UPDATE cases SET params=?, updated_at=datetime('now') WHERE id=?", (json.dumps(params), case_id))
        conn.commit()
        append_event(conn, case_id, "plan.approved", {"panel_size": body.panel_size, "quoted_price_inr": quote["quoted_price_inr"],
                                                      "label": quote["label"]})
        tasks.add_task(runner.continue_case, case_id)
        return {"id": case_id, "state": "PLANNED", "quote": quote}
    finally:
        conn.close()


class OutreachApproval(BaseModel):
    refs: list[str] = Field(min_length=1)   # the experts to invite (their `ref` from `invites`); every other waiting invitation is dropped


@router.post("/customer/cases/{case_id}/approve-outreach")
def approve_outreach(case_id: str, body: OutreachApproval):
    """The customer's click on the anonymised invitations. Listed experts are invited, the rest are dropped, and the case
    starts collecting. Each invitation is its own logged approval and goes out through the teammate-only mail gate."""
    conn = db.connect()
    try:
        case = conn.execute("SELECT state FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(404, "no such case")
        if case["state"] != "AWAITING_APPROVAL":
            raise HTTPException(409, f"the case is {case['state']}, not waiting for invitation approval")
        try:
            result = queue.approve_batch(conn, case_id, body.refs)
        except queue.QueueError as e:
            raise HTTPException(e.status, e.message)
        if result["sent"]:
            runner.set_state(conn, case_id, "COLLECTING")
        return {**result, "state": "COLLECTING" if result["sent"] else "AWAITING_APPROVAL"}
    finally:
        conn.close()


def _stream(case_id: str, after: int, last_event_id: int | None, transform: Callable | None) -> StreamingResponse:
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
                    shown = transform(conn, case_id, r["type"], payload) if transform else payload
                    yield (f"id: {r['id']}\nevent: {r['type']}\n"
                           f"data: {json.dumps({'id': r['id'], 'type': r['type'], 'at': r['created_at'], **shown})}\n\n")
                    if r["type"] == "job.paused" or (r["type"] == "case.state" and payload.get("state") in TERMINAL_STATES):
                        return
                await asyncio.sleep(0.4)
        finally:
            conn.close()

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/cases/{case_id}/events")
async def stream_events(case_id: str, after: int = Query(0), last_event_id: int | None = Header(None)):
    """Operator stream: full results. Replays from `after` (or Last-Event-ID), then follows live until the job pauses or ends."""
    return _stream(case_id, after, last_event_id, None)


@router.get("/customer/cases/{case_id}/events")
async def stream_customer_events(case_id: str, after: int = Query(0), last_event_id: int | None = Header(None)):
    """Customer stream: the same events with names, profile links and addresses removed."""
    return _stream(case_id, after, last_event_id, views.redact_event)
