import json
import sqlite3

import httpx
import pytest

from app.core import config, db
from app.core.events import append_event, verify_chain
from app.crustdata.client import CreditCapExceeded, CrustdataClient, CrustdataError


@pytest.fixture
def conn():
    return db.connect(":memory:")


def make_client(conn, handler, **kw):
    return CrustdataClient(conn, case_id="c1", transport=httpx.MockTransport(handler), api_key="test", **kw)


def ok(request):
    return httpx.Response(200, json={"profiles": [], "echo": json.loads(request.content)}, headers={"X-Credits-Used": "1.5"})


def test_call_is_logged_with_credits_and_event(conn):
    client = make_client(conn, ok)
    data, call_id = client.post("/person/search", {"filters": {}}, "test")
    row = conn.execute("SELECT * FROM crustdata_calls WHERE call_id=?", (call_id,)).fetchone()
    assert row["credits"] == 1.5 and row["status"] == 200 and row["cache_hit"] == 0
    assert conn.execute("SELECT type FROM events").fetchone()["type"] == "crustdata.call"
    assert verify_chain(conn) == (True, None)


def test_dev_limit_applied_not_in_demo(conn, monkeypatch):
    monkeypatch.delenv("SYNEX_DEMO", raising=False)
    data, _ = make_client(conn, ok).post("/person/search", {"limit": 100}, "t")
    assert data["echo"]["limit"] == 5
    monkeypatch.setenv("SYNEX_DEMO", "1")
    data, _ = make_client(conn, ok).post("/person/search", {"limit": 100}, "t")
    assert data["echo"]["limit"] == 100


def test_credit_cap_blocks_next_call(conn):
    client = make_client(conn, ok, credit_cap=1.0)
    client.post("/company/enrich", {}, "t")
    with pytest.raises(CreditCapExceeded):
        client.post("/company/enrich", {}, "t")


def test_error_is_logged_and_raised(conn):
    client = make_client(conn, lambda r: httpx.Response(400, text="bad"))
    with pytest.raises(CrustdataError):
        client.post("/person/search", {}, "t")
    assert conn.execute("SELECT status, error FROM crustdata_calls").fetchone()["error"] == "bad"


def test_cache_only_in_dev(conn, monkeypatch):
    calls = []

    def handler(r):
        calls.append(1)
        return ok(r)

    monkeypatch.setenv("SYNEX_DEV_CACHE", "1")
    monkeypatch.delenv("SYNEX_DEMO", raising=False)
    c = make_client(conn, handler)
    c.post("/person/search", {"a": 1}, "t")
    c.post("/person/search", {"a": 1}, "t")
    assert len(calls) == 1
    assert conn.execute("SELECT COUNT(*) c FROM crustdata_calls WHERE cache_hit=1").fetchone()["c"] == 1
    monkeypatch.setenv("SYNEX_DEMO", "1")
    assert config.dev_cache_enabled() is False
    c.post("/person/search", {"a": 1}, "t")
    assert len(calls) == 2


def test_events_are_append_only_and_chained(conn):
    append_event(conn, "c1", "a", {"x": 1})
    append_event(conn, "c1", "b", {"x": 2})
    assert verify_chain(conn) == (True, None)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE events SET type='z' WHERE id=1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM events")
    make_client(conn, ok).post("/company/enrich", {}, "t")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM crustdata_calls")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE crustdata_calls SET credits=0")


def test_web_origins_default_and_extra(monkeypatch):
    monkeypatch.delenv("SYNEX_WEB_ORIGINS", raising=False)
    assert config.web_origins() == ["http://localhost:3000", "http://127.0.0.1:3000"]
    monkeypatch.setenv("SYNEX_WEB_ORIGINS", "http://localhost:3001, http://127.0.0.1:3001")
    assert config.web_origins()[2:] == ["http://localhost:3001", "http://127.0.0.1:3001"]


def test_network_errors_are_retried_then_logged(conn, monkeypatch):
    monkeypatch.setattr("app.crustdata.client.time.sleep", lambda s: None)
    calls = []

    def flaky(request):
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError("Temporary failure in name resolution")
        return ok(request)

    data, _ = make_client(conn, flaky).post("/person/search", {}, "t")
    assert len(calls) == 3 and data["profiles"] == []
    down = make_client(conn, lambda r: (_ for _ in ()).throw(httpx.ConnectError("down")))
    with pytest.raises(CrustdataError):
        down.post("/person/search", {"x": 1}, "t")
    assert conn.execute("SELECT COUNT(*) c FROM crustdata_calls WHERE status=0").fetchone()["c"] == 1


def test_secrets_pasted_with_whitespace_are_trimmed(monkeypatch):
    monkeypatch.setenv("CRUSTDATA_API_KEY", "  abc123\n")
    monkeypatch.setenv("SYNEX_OPERATOR_KEY", "k3y\n")
    assert config.crustdata_key() == "abc123" and config.operator_key() == "k3y"


def test_rate_limited_call_waits_and_retries(conn, monkeypatch):
    slept = []
    monkeypatch.setattr("app.crustdata.client.time.sleep", lambda s: slept.append(s))
    calls = []

    def limited(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, json={"error": "rate"}, headers={"Retry-After": "2"})
        return ok(request)

    data, _ = make_client(conn, limited).post("/company/identify", {"names": ["x"]}, "t")
    assert len(calls) == 3 and slept == [2.0, 2.0] and "echo" in data


def test_pacing_spaces_calls_to_the_account_rate(monkeypatch):
    from app.crustdata import client as cl
    t = {"now": 100.0}
    slept = []
    monkeypatch.setattr(cl.time, "monotonic", lambda: t["now"])
    monkeypatch.setattr(cl.time, "sleep", lambda s: (slept.append(round(s, 1)), t.__setitem__("now", t["now"] + s)))
    cl._last_call.clear()
    cl._pace("/company/identify")
    cl._pace("/company/identify")
    assert slept == [12.6]          # 5 a minute, with a 5% margin
