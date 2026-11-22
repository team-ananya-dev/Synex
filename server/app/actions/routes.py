"""Operator view of outreach. It shows real people's details: operator screens only, never the customer's."""
from fastapi import APIRouter

from ..core import db
from . import queue

router = APIRouter()


@router.get("/approvals")
def list_approvals(status: str | None = None, case_id: str | None = None):
    """Every outreach draft and what happened to it. Read-only: invitations are approved by the customer, not by the operator."""
    conn = db.connect()
    try:
        return queue.list_items(conn, status, case_id)
    finally:
        conn.close()
