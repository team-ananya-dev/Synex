"""Crustdata client. Every call is logged to crustdata_calls and the audit chain.

Dev safeguards (all off when SYNEX_DEMO=1):
  - search results are capped at SYNEX_DEV_LIMIT (default 5)
  - real responses can be cached locally when SYNEX_DEV_CACHE=1
A per-case credit cap applies in every mode.
"""
import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone

import httpx

from ..core import config
from ..core.events import append_event

BASE_URL = "https://api.crustdata.com"
API_VERSION = "2025-11-01"
RATE_LIMIT_WAITS = (2, 4, 8, 15, 30, 30)  # seconds before each of up to 6 retries of a 429
LIMITED_ENDPOINTS = {"/person/search", "/company/search", "/job/search"}


class CreditCapExceeded(RuntimeError):
    pass


class CrustdataError(RuntimeError):
    def __init__(self, status: int, body: str, call_id: str):
        super().__init__(f"Crustdata {status} (call {call_id}): {body[:300]}")
        self.status, self.body, self.call_id = status, body, call_id


class CrustdataClient:
    def __init__(
        self,
        conn: sqlite3.Connection,
        case_id: str | None = None,
        credit_cap: float = 25.0,
        transport: httpx.BaseTransport | None = None,
        api_key: str | None = None,
    ):
        self.conn = conn
        self.case_id = case_id
        self.credit_cap = credit_cap
        self._http = httpx.Client(
            base_url=BASE_URL,
            timeout=60,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key or config.crustdata_key()}",
                "x-api-version": API_VERSION,
            },
        )

    def credits_spent(self) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(credits), 0) AS c FROM crustdata_calls WHERE case_id IS ?", (self.case_id,)
        ).fetchone()
        return float(row["c"])

    def post(self, endpoint: str, body: dict, purpose: str) -> tuple[dict | list, str]:
        """Return (response json, call_id). The call_id is what memo claims cite."""
        body = json.loads(json.dumps(body))
        limit = config.dev_limit()
        if limit is not None and endpoint in LIMITED_ENDPOINTS:
            body["limit"] = min(int(body.get("limit", limit)), limit)

        if self.credits_spent() >= self.credit_cap:
            raise CreditCapExceeded(f"case {self.case_id}: {self.credits_spent():.2f} of {self.credit_cap} credits used")

        key = hashlib.sha256(json.dumps([endpoint, body], sort_keys=True).encode()).hexdigest()
        if config.dev_cache_enabled():
            hit = self.conn.execute("SELECT response FROM dev_cache WHERE key = ?", (key,)).fetchone()
            if hit:
                return self._log(endpoint, body, purpose, 200, 0.0, 0, json.loads(hit["response"]), None, True)

        started = time.monotonic()
        resp = None
        for attempt in range(3):  # a network error (DNS, reset, timeout) is retried twice before it counts
            try:
                resp = self._http.post(endpoint, json=body)
                break
            except httpx.TransportError as e:
                if attempt == 2:
                    latency = int((time.monotonic() - started) * 1000)
                    call_id = self._log(endpoint, body, purpose, 0, 0.0, latency, None, f"{type(e).__name__}: {e}", False)[1]
                    raise CrustdataError(0, f"{type(e).__name__}: {e}", call_id) from e
                time.sleep(1 + attempt)
        for wait in RATE_LIMIT_WAITS:  # rate limited: pause (longer if Crustdata says so) and ask again; demo mode fires many calls
            if resp.status_code != 429:
                break
            time.sleep(max(wait, float(resp.headers.get("Retry-After") or 0)))
            resp = self._http.post(endpoint, json=body)
        latency = int((time.monotonic() - started) * 1000)
        credits = float(resp.headers.get("X-Credits-Used") or 0)

        if resp.status_code != 200:
            call_id = self._log(endpoint, body, purpose, resp.status_code, credits, latency, None, resp.text[:2000], False)[1]
            raise CrustdataError(resp.status_code, resp.text, call_id)

        data = resp.json()
        if config.dev_cache_enabled():
            self.conn.execute(
                "INSERT OR REPLACE INTO dev_cache (key, endpoint, response, created_at) VALUES (?,?,?,?)",
                (key, endpoint, json.dumps(data), datetime.now(timezone.utc).isoformat()),
            )
            self.conn.commit()
        return self._log(endpoint, body, purpose, 200, credits, latency, data, None, False)

    def get(self, endpoint: str, purpose: str) -> dict:
        resp = self._http.get(endpoint)
        resp.raise_for_status()
        return resp.json()

    def _log(self, endpoint, body, purpose, status, credits, latency, data, error, cache_hit):
        call_id = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO crustdata_calls (call_id, case_id, purpose, endpoint, request, status, credits,"
            " latency_ms, cache_hit, response, error, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (call_id, self.case_id, purpose, endpoint, json.dumps(body, sort_keys=True), status, credits, latency,
             int(cache_hit), json.dumps(data) if data is not None else None, error,
             datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        # event payload carries no profile data, only what the call was and cost
        append_event(self.conn, self.case_id, "crustdata.call", {
            "call_id": call_id, "endpoint": endpoint, "purpose": purpose, "status": status,
            "credits": credits, "cache_hit": cache_hit,
        })
        return (data, call_id) if status == 200 else (None, call_id)
