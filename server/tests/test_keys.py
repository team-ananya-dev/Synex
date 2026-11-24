"""Bring your own key: the browser's keys are used, never stored, and a hosted site with no .env keys needs them."""
import sqlite3

from tests.test_runner import api, events  # noqa: F401  (fixture and helper)
from app.core import config, db, keys, llm

BROWSER = {"X-Anthropic-Key": "sk-ant-browser-secret\n", "X-Crustdata-Key": "crust-browser-secret"}


def hosted(monkeypatch):
    monkeypatch.delenv("SYNEX_ANTHROPIC_KEY", raising=False)
    monkeypatch.delenv("CRUSTDATA_API_KEY", raising=False)


def test_hosted_site_without_keys_refuses_up_front(api, monkeypatch):
    client, _ = api
    hosted(monkeypatch)
    r = client.post("/cases", json={"question": "What does Acme do?"})
    assert r.status_code == 400 and r.json()["code"] == "missing_key"
    assert client.get("/cases").json() == []   # no half-made case


def test_visitor_key_runs_the_case_and_is_not_stored(api, monkeypatch):
    client, fake = api
    hosted(monkeypatch)
    used = []
    monkeypatch.setattr(llm.anthropic, "Anthropic", lambda **k: (used.append(k["api_key"]), fake["v"])[1])
    cid = client.post("/cases", json={"question": "What does Acme do?"}, headers=BROWSER).json()["id"]
    events(client, cid)
    assert client.get(f"/cases/{cid}").json()["state"] == "PLANNED"
    assert used and set(used) == {"sk-ant-browser-secret"}   # newline stripped
    # the case remembers its keys, so the approval works without resending them
    assert client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 1}).status_code == 200
    # a case that only ever had the Anthropic key cannot start sourcing
    only = {"X-Anthropic-Key": "sk-ant-browser-secret"}
    c2 = client.post("/cases", json={"question": "What does Acme do?"}, headers=only).json()["id"]
    events(client, c2)
    r = client.post(f"/customer/cases/{c2}/approve-plan", json={"panel_size": 1})
    assert r.status_code == 400 and "Crustdata" in r.json()["detail"]
    # nowhere on disk
    raw = open(db.db_path(), "rb").read() if hasattr(db, "db_path") else open(config.db_path(), "rb").read()
    assert b"browser-secret" not in raw


def test_env_key_still_works_for_a_local_clone(api):
    client, _ = api   # fixture sets the .env keys
    assert client.post("/cases", json={"question": "What does Acme do?"}).status_code == 201


def test_own_key_is_not_held_to_the_shared_budget(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(llm, "BUDGET_USD", 0.0)
    # server's key: budget reached
    c = db.connect()
    try:
        llm.call_json(c, purpose="t", system="s", user="u", schema={"type": "object", "properties": {}}, case_id=None)
        raise AssertionError("expected BudgetExceeded")
    except llm.BudgetExceeded:
        pass
    keys.remember("case1", {"anthropic": "mine"})
    reply, _ = llm.call_json(c, purpose="t", system="s", user="u", schema={"type": "object", "properties": {}}, case_id="case1")
    assert reply is not None


def test_scrub_removes_the_key():
    keys.remember("c9", {"anthropic": "sk-ant-xyz"})
    assert "sk-ant-xyz" not in keys.scrub("auth failed for sk-ant-xyz", "c9")
