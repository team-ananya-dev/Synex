"""Operator approval queue. These routes show real people's details: operator screens only, never the customer's."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import db
from . import queue

router = APIRouter()


class Decision(BaseModel):
    approver: str  # a registered team member: dev or ananya


def _run(fn, outreach_id: int, approver: str):
    conn = db.connect()
    try:
        return fn(conn, outreach_id, approver)
    except queue.QueueError as e:
        raise HTTPException(e.status, e.message)
    finally:
        conn.close()


@router.get("/approvals")
def list_approvals(status: str | None = None, case_id: str | None = None):
    conn = db.connect()
    try:
        return queue.list_items(conn, status, case_id)
    finally:
        conn.close()


@router.post("/approvals/{outreach_id}/approve")
def approve(outreach_id: int, body: Decision):
    return _run(queue.approve, outreach_id, body.approver)


@router.post("/approvals/{outreach_id}/reject")
def reject(outreach_id: int, body: Decision):
    return _run(queue.reject, outreach_id, body.approver)
