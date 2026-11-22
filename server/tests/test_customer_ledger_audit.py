import json
import sqlite3

import pytest

from app.actions import ledger, queue
from app.core import db
from tests.test_runner import api, events, start  # noqa: F401  (fixtures and helpers)

SECRETS = ["Quentin", "Zephyr", "example.test", "Secret headline", "Pune", "linkedin", "@", "/expert/", "gmail"]


def customer_text(client, cid):
    view = json.dumps(client.get(f"/customer/cases/{cid}").json())
    with client.stream("GET", f"/customer/cases/{cid}/events?after=0") as r:
        stream = "".join(r.iter_text())
    return view, stream


def test_customer_view_and_stream_never_contain_names_links_or_addresses(api):
    client, _ = api
    cid = start(client)
    # events after the pause need a second connection; read the whole log through the redacting transform
    view, stream = customer_text(client, cid)
    from app.jobs import views
    conn = db.connect()
    redacted = json.dumps([views.redact_event(conn, cid, r["type"], json.loads(r["payload"]))
                           for r in conn.execute("SELECT type, payload FROM events WHERE case_id=? ORDER BY id", (cid,))])
    for text in (view, stream, redacted):
        for secret in SECRETS:
            assert secret not in text, f"{secret!r} leaked"
    assert "gmail.com" not in redacted  # the teammate address is not shown to the customer either


def test_operator_view_still_has_the_details(api):
    client, _ = api
    cid = start(client)
    assert "Quentin" in json.dumps(client.get(f"/cases/{cid}").json())


def test_customer_view_has_cards_with_evidence_and_screening_reasons(api):
    client, _ = api
    cid = start(client)
    v = client.get(f"/customer/cases/{cid}").json()
    card = v["panel"]["1"][0]
    assert set(card) == {"ref", "role", "company", "tenure_months", "left_year", "country", "fit", "score", "reason", "evidence", "evidence_hidden"}
    assert card["ref"].startswith("E") and card["country"] == "India" and card["company"] == "Acme"
    assert card["evidence"] == ["Operations Manager"] and card["evidence_hidden"] == 0
    sc = v["screening"]["1"]
    assert sc["considered"] == 3 and sc["fail"] == 2 and all(e["reasons"] and e["ref"] for e in sc["excluded"])
    assert v["outreach"] == {"DRAFTED": 1} and v["approval"] == {"panel_size": 2, "budget": 1000, "hold": 200}


def test_expert_ref_is_stable_per_case_and_differs_across_cases():
    from app.jobs.views import expert_ref
    assert expert_ref("c1", 5) == expert_ref("c1", 5) != expert_ref("c2", 5) != expert_ref("c1", 6)


def test_quote_is_shown_while_waiting_and_budget_is_checked(api):
    client, _ = api
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    v = client.get(f"/customer/cases/{cid}").json()
    assert v["state"] == "PLANNED" and v["quote"] == {"subquestions": 2, "price_per_subquestion": 100.0, "hold_amount": 200.0,
                                                      "currency": "USD (simulated)"}
    low = client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 2, "budget": 150})
    assert low.status_code == 422 and "200" in low.json()["detail"]
    assert client.get(f"/cases/{cid}").json()["state"] == "PLANNED"     # nothing was spent or started
    assert client.get(f"/customer/cases/{cid}").json()["ledger"]["entries"] == []


def test_plan_approval_rules(api):
    client, _ = api
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    assert client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 0, "budget": 500}).status_code == 422
    assert client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 9, "budget": 500}).status_code == 422
    assert client.post("/customer/cases/nope/approve-plan", json={"panel_size": 2, "budget": 500}).status_code == 404
    assert client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 2, "budget": 500}).status_code == 200
    again = client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 2, "budget": 500})
    assert again.status_code == 409                                      # one hold, one run
    assert len(client.get(f"/customer/cases/{cid}").json()["ledger"]["entries"]) == 1


def test_refused_case_cannot_be_approved(api):
    from tests.test_runner import FakeAnthropic
    client, fake = api
    fake["v"] = FakeAnthropic("refuse")
    cid = client.post("/cases", json={"question": "Tell me Acme's unreleased revenue"}).json()["id"]
    assert client.post(f"/customer/cases/{cid}/approve-plan", json={"panel_size": 2, "budget": 500}).status_code == 409


def test_panel_size_limits_the_number_of_drafts(api):
    client, _ = api
    cid = start(client, panel_size=1)
    items = client.get("/approvals", params={"case_id": cid}).json()
    assert len(items) == 1                                               # only one person passes in the fixture anyway
    assert client.get(f"/customer/cases/{cid}").json()["ledger"]["balance"]["held"] == 200.0


# ---- ledger ---------------------------------------------------------------------------------------

@pytest.fixture
def conn():
    return db.connect(":memory:")


def test_ledger_hold_capture_release(conn):
    ledger.place_hold(conn, "c1", 300, "customer")
    ledger.capture(conn, "c1", 1, 100, "system")
    assert ledger.balance(conn, "c1") == {"held": 300.0, "captured": 100.0, "released": 0.0, "remaining": 200.0, "currency": "USD (simulated)"}
    ledger.release_remaining(conn, "c1", "system")
    b = ledger.balance(conn, "c1")
    assert b["remaining"] == 0 and b["released"] == 200.0
    assert ledger.release_remaining(conn, "c1", "system") is None       # nothing left to release
    assert all(e["currency"] == "USD (simulated)" for e in ledger.entries(conn, "c1"))
    types = [r["type"] for r in conn.execute("SELECT type FROM events")]
    assert types == ["ledger.hold", "ledger.capture", "ledger.release"]


def test_ledger_refuses_a_second_hold_and_an_oversized_capture(conn):
    ledger.place_hold(conn, "c1", 100, "customer")
    with pytest.raises(ledger.LedgerError):
        ledger.place_hold(conn, "c1", 100, "customer")
    with pytest.raises(ledger.LedgerError):
        ledger.capture(conn, "c1", 1, 101, "system")


def test_ledger_is_append_only(conn):
    ledger.place_hold(conn, "c1", 100, "customer")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE ledger SET amount=1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM ledger")


# ---- expert page hand-off ---------------------------------------------------------------------------

def test_expert_context_from_token(api):
    client, _ = api
    cid = start(client)
    conn = db.connect()
    token = conn.execute("SELECT token FROM outreach WHERE case_id=?", (cid,)).fetchone()["token"]
    ctx = queue.expert_context(conn, token)
    assert ctx["status"] == "DRAFTED" and ctx["first_name"] == "Quentin" and ctx["case_id"] == cid
    assert [q["index"] for q in ctx["subquestions"]] == [1, 2] and all(q["text"] for q in ctx["subquestions"])
    assert "customer" not in json.dumps(ctx).lower() and queue.expert_context(conn, "nope") is None


# ---- audit and cost endpoints ----------------------------------------------------------------------

def test_audit_events_verify_and_costs(api):
    client, _ = api
    cid = start(client)
    ev = client.get("/audit/events", params={"case_id": cid, "limit": 5}).json()
    assert len(ev) == 5 and ev[0]["prev_hash"] and ev[1]["prev_hash"] == ev[0]["hash"]
    v = client.get("/audit/verify").json()
    assert v["ok"] is True and v["first_bad_event_id"] is None and v["events_checked"] > 10
    c = client.get(f"/cases/{cid}/costs").json()
    assert c["totals"]["crustdata_credits"] > 0 and c["totals"]["model_usd"] > 0
    assert {"call_id", "endpoint", "credits", "cache_hit"} <= set(c["crustdata_calls"][0])
    assert "prompt" not in c["llm_calls"][0] and "response" not in c["llm_calls"][0]
    t = client.get("/costs").json()
    assert t["model_budget_usd"] == 25 and t["model_remaining_usd"] < 25 and t["crustdata_calls"] > 0


def test_audit_verify_detects_tampering(api):
    client, _ = api
    start(client)
    raw = sqlite3.connect(db.config.db_path())
    raw.execute("DROP TRIGGER events_no_update")          # an attacker with file access removes the guard...
    raw.execute("UPDATE events SET payload='{}' WHERE id=3")  # ...and edits an event
    raw.commit()
    v = client.get("/audit/verify").json()
    assert v["ok"] is False and v["first_bad_event_id"] == 3


def test_headline_evidence_is_hidden_from_the_card_but_counted():
    from app.jobs.views import card
    p = {"person_id": 1, "title": "Cafe Manager", "function": None, "role_description": None, "skills": [], "company_id": 9,
         "tenure_months": 14, "end_date": "2026-01-01", "country": "India", "fit": "partial", "score": 65, "reason": "r",
         "evidence": ["Store Operations Manager | Quick Commerce"], "headline": "Store Operations Manager | Quick Commerce"}
    c = card("c1", p, {"9": "Acme"})
    assert c["evidence"] == [] and c["evidence_hidden"] == 1 and "Store Operations" not in json.dumps(c)
