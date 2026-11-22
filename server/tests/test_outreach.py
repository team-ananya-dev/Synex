import json

import pytest
from fastapi.testclient import TestClient

from app.actions import mail, queue
from app.core import db
from app.core.events import verify_chain
from app.main import app
from app.stages import s6_outreach_writer as s6
from tests.test_runner import api, events  # noqa: F401  (fixtures and helpers)


class FakeSMTP:
    sent = []
    fail = False

    def __init__(self, host, port, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def send_message(self, msg):
        if FakeSMTP.fail:
            raise ConnectionRefusedError("mailpit is not running")
        FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def run_case(client):
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    items = client.get("/approvals", params={"case_id": cid}).json()
    return cid, items


def test_drafts_wait_in_the_queue_and_nothing_is_sent(api, smtp):
    client, _ = api
    cid, items = run_case(client)
    assert len(items) == 1 and items[0]["status"] == "DRAFTED" and smtp.sent == []
    item = items[0]
    assert item["to_address"] in mail.ALLOWLIST          # a teammate plays the expert
    assert item["subquestion_indices"] == [1, 2]
    assert "{{" not in item["body"] and "/expert/" in item["body"] and item["body"].startswith("Hello P1,")
    assert "token" not in item
    assert client.get(f"/cases/{cid}").json()["state"] == "AWAITING_APPROVAL"


def test_approve_sends_to_the_teammate_inbox(api, smtp):
    client, _ = api
    cid, items = run_case(client)
    r = client.post(f"/approvals/{items[0]['id']}/approve", json={"approver": "Dev"}).json()
    assert r["status"] == "SENT" and r["decided_by"] == "dev" and r["sent_at"]
    msg = smtp.sent[0]
    assert msg["To"] == items[0]["to_address"] and msg["X-Synex-Case"] == cid
    types = [r["type"] for r in db.connect().execute("SELECT type FROM events WHERE case_id=?", (cid,))]
    assert "approval.approved" in types and "mail.sent" in types
    assert client.post(f"/approvals/{items[0]['id']}/approve", json={"approver": "dev"}).status_code == 409  # no double send
    assert len(smtp.sent) == 1


def test_reject_sends_nothing(api, smtp):
    client, _ = api
    _, items = run_case(client)
    r = client.post(f"/approvals/{items[0]['id']}/reject", json={"approver": "ananya"}).json()
    assert r["status"] == "REJECTED" and smtp.sent == []


def test_only_registered_team_members_can_decide(api, smtp):
    client, _ = api
    _, items = run_case(client)
    assert client.post(f"/approvals/{items[0]['id']}/approve", json={"approver": "stranger"}).status_code == 403
    assert smtp.sent == [] and client.get("/approvals").json()[0]["status"] == "DRAFTED"
    assert client.post("/approvals/999/approve", json={"approver": "dev"}).status_code == 404


def test_allowlist_blocks_any_other_address_and_records_it(api, smtp):
    client, _ = api
    conn = db.connect()
    oid = queue.create_draft(conn, case_id="c1", person_id=5, name="X Y", persona_title="t", persona_company="c", tenure_months=12,
                             subquestion_indices=[1], flags=[], to_address="stranger@example.com", subject="s",
                             body_template="Hello {{first_name}} {{link}}", link_base="http://x", llm_call_id=None)
    r = client.post(f"/approvals/{oid}/approve", json={"approver": "dev"}).json()
    assert r["status"] == "BLOCKED" and "allowlist" in r["block_reason"]
    assert smtp.sent == []
    assert conn.execute("SELECT COUNT(*) c FROM events WHERE type='mail.blocked'").fetchone()["c"] == 1
    assert verify_chain(conn) == (True, None)


def test_send_mail_itself_refuses_without_going_through_the_queue(smtp):
    with pytest.raises(mail.MailBlocked):
        mail.send_mail("stranger@example.com", "s", "b")
    assert smtp.sent == []


def test_mail_failure_is_recorded_not_hidden(api, smtp):
    client, _ = api
    _, items = run_case(client)
    smtp.fail = True
    r = client.post(f"/approvals/{items[0]['id']}/approve", json={"approver": "dev"}).json()
    assert r["status"] == "FAILED" and "mailpit is not running" in r["block_reason"]


@pytest.mark.parametrize("body,msg", [
    ("Hello {{first_name}}, simulated. no link", "exactly once"),
    ("Hello {{first_name}}, {{link}} {{link}} simulated", "exactly once"),
    ("Hello {{first_name}}, {{link}} see https://evil.test simulated", "no links"),
    ("Hello {{first_name}}, {{link}} payment is real", "simulated"),
    ("Hello Rohan Gamre, {{link}} {{first_name}} simulated", "name"),
    ("Hello, {{link}} simulated", "first_name"),
    ("Hello {{first_name}}, **bold** {{link}} simulated", "plain text"),
])
def test_draft_checks(body, msg):
    with pytest.raises(ValueError, match=msg):
        s6.validate({"subject": "Hi", "body": body}, "Rohan Gamre")


def test_good_draft_passes():
    s6.validate({"subject": "Hi", "body": "Hello {{first_name}}, {{link}} payment is simulated."}, "Rohan Gamre")
