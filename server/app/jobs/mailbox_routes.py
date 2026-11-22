"""Operator view of the local mailbox (Mailpit). On a hosted deployment Mailpit runs inside the API container
and is not public, so the operator reads the invitations here. Read-only."""
import httpx
from fastapi import APIRouter, HTTPException

from ..core import config

router = APIRouter()


def _get(path: str):
    try:
        r = httpx.get(f"{config.mailpit_api()}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"mailbox unavailable: {type(e).__name__}")


@router.get("/mailbox")
def mailbox():
    data = _get("/api/v1/messages?limit=200")
    return [{"id": m["ID"], "to": [t["Address"] for t in m.get("To") or []], "subject": m.get("Subject"),
             "created": m.get("Created"), "snippet": m.get("Snippet")} for m in data.get("messages", [])]


@router.get("/mailbox/{message_id}")
def mailbox_message(message_id: str):
    m = _get(f"/api/v1/message/{message_id}")
    return {"id": m["ID"], "to": [t["Address"] for t in m.get("To") or []], "subject": m.get("Subject"),
            "created": m.get("Date"), "text": m.get("Text"), "headers": {k: v for k, v in (m.get("Headers") or {}).items()
                                                                          if k.lower().startswith("x-synex")}}
