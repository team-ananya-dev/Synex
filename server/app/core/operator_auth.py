"""Operator routes show real people's names and full answers. On a hosted deployment they need the operator key,
sent as the X-Operator-Key header (or ?key= for the event stream, which cannot send headers)."""
import hmac
import re

from fastapi import Request
from fastapi.responses import JSONResponse

from . import config

OPERATOR_PATH = re.compile(r"^/(operator|approvals|audit|costs|mailbox)(/|$)|^/cases/[^/]+(/events|/costs|/retry)?$|^/cases$")


def is_operator_route(method: str, path: str) -> bool:
    if method == "OPTIONS" or (method == "POST" and path == "/cases"):  # asking a question is the customer's
        return False
    return bool(OPERATOR_PATH.match(path))


async def require_operator_key(request: Request, call_next):
    key = config.operator_key()
    if key and is_operator_route(request.method, request.url.path):
        given = request.headers.get("x-operator-key") or request.query_params.get("key") or ""
        if not hmac.compare_digest(given, key):
            return JSONResponse({"detail": "operator key required"}, status_code=401)
    return await call_next(request)
