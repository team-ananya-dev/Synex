import json

import pytest
from fastapi.testclient import TestClient

from app.actions import mail, queue
from app.core import db
from app.core.events import verify_chain
from app.main import app
from app.stages import s6_outreach_writer as s6
from tests.test_runner import api, events, start  # noqa: F401  (fixtures and helpers)


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
    cid = start(client)
    items = client.get("/approvals", params={"case_id": cid}).json()
    return cid, items


def test_drafts_wait_in_the_queue_and_nothing_is_sent(api, smtp):
    client, _ = api
    cid, items = run_case(client)
    assert len(items) == 1 and items[0]["status"] == "DRAFTED" and smtp.sent == []
    item = items[0]
    assert item["to_address"] in mail.ALLOWLIST          # a teammate plays the expert
    assert item["subquestion_indices"] == [1, 2]
    assert "{{" not in item["body"] and "/expert/" in item["body"] and item["body"].startswith("Hello Quentin,")
    assert "token" not in item
    assert client.get(f"/cases/{cid}").json()["state"] == "AWAITING_APPROVAL"


def refs_of(client, cid):
    return [i["ref"] for i in client.get(f"/customer/cases/{cid}").json()["invites"]]


def test_customer_sees_anonymised_invitations_with_nothing_to_contact_them_by(api, smtp):
    client, _ = api
    cid, items = run_case(client)
    inv = client.get(f"/customer/cases/{cid}").json()["invites"]
    assert len(inv) == 1 and inv[0]["status"] == "DRAFTED" and inv[0]["selected_by_default"] is True
    text = json.dumps(inv)
    for secret in ("Quentin", "Zephyr", "gmail.com", "/expert/", "example.test", items[0]["body"].split("/expert/")[1].split()[0]):
        assert secret not in text, f"{secret!r} leaked into the customer invitation preview"
    assert inv[0]["preview"].startswith("Hello [first name],") and "[private link]" in inv[0]["preview"]
    assert inv[0]["subquestion_indices"] == [1, 2] and inv[0]["subject"]
    assert smtp.sent == []                                   # nothing goes out before the customer approves


def test_customer_approval_sends_to_the_teammate_inbox_and_starts_collecting(api, smtp):
    client, _ = api
    cid, items = run_case(client)
    r = client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs_of(client, cid)})
    assert r.status_code == 200 and r.json() == {"sent": 1, "dropped": 0, "blocked": 0, "failed": 0, "state": "COLLECTING"}
    msg = smtp.sent[0]
    assert msg["To"] == items[0]["to_address"] and msg["To"] in mail.ALLOWLIST and msg["X-Synex-Case"] == cid
    assert "Hello Quentin," in msg.get_content()               # the expert's own email has the greeting and the real link
    assert client.get(f"/cases/{cid}").json()["state"] == "COLLECTING"
    row = client.get("/approvals", params={"case_id": cid}).json()[0]
    assert row["status"] == "SENT" and row["decided_by"] == "customer" and row["sent_at"]
    types = [r["type"] for r in db.connect().execute("SELECT type FROM events WHERE case_id=?", (cid,))]
    assert types.count("approval.approved") == 1 and "mail.sent" in types and "outreach.batch_approved" in types


def test_each_email_is_its_own_logged_approval(api, smtp):
    client, _ = api
    cid, _ = run_case(client)
    conn = db.connect()
    for pid in (11, 12):                                        # two more waiting invitations in the same case
        queue.create_draft(conn, case_id=cid, person_id=pid, name="A B", persona_title="t", persona_company="c", tenure_months=12,
                           subquestion_indices=[1], flags=[], to_address=mail.ALLOWLIST[0], subject="s",
                           body_template="Hello {{first_name}} {{link}} simulated", link_base="http://x", llm_call_id=None)
    refs = [i["ref"] for i in client.get(f"/customer/cases/{cid}").json()["invites"]]
    assert len(refs) == 3
    client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs})
    approvals = [json.loads(r["payload"]) for r in conn.execute("SELECT payload FROM events WHERE case_id=? AND type='approval.approved'", (cid,))]
    assert len(approvals) == 3 and all(a["by"] == "customer" for a in approvals) and len(smtp.sent) == 3


def test_experts_the_customer_leaves_out_are_dropped_not_contacted(api, smtp):
    client, _ = api
    cid, _ = run_case(client)
    conn = db.connect()
    queue.create_draft(conn, case_id=cid, person_id=11, name="A B", persona_title="t", persona_company="c", tenure_months=12,
                       subquestion_indices=[1], flags=[], to_address=mail.ALLOWLIST[0], subject="s",
                       body_template="Hello {{first_name}} {{link}} simulated", link_base="http://x", llm_call_id=None)
    refs = refs_of(client, cid)
    r = client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs[:1]}).json()
    assert r["sent"] == 1 and r["dropped"] == 1 and len(smtp.sent) == 1
    statuses = sorted(i["status"] for i in client.get(f"/customer/cases/{cid}").json()["invites"])
    assert statuses == ["REJECTED", "SENT"]


def test_flagged_experts_are_not_selected_by_default_and_show_why(api, smtp):
    client, _ = api
    cid, _ = run_case(client)
    conn = db.connect()
    queue.create_draft(conn, case_id=cid, person_id=12, name="A B", persona_title="Store Manager", persona_company="c", tenure_months=12,
                       subquestion_indices=[1], flags=[{"rule": "rule_competitor", "reason": "now a Store Manager at a direct competitor"}],
                       to_address=mail.ALLOWLIST[0], subject="s", body_template="Hello {{first_name}} {{link}} simulated",
                       link_base="http://x", llm_call_id=None)
    inv = client.get(f"/customer/cases/{cid}").json()["invites"]
    flagged = next(i for i in inv if i["flagged"])
    assert flagged["selected_by_default"] is False and "competitor" in flagged["flag_reasons"][0]
    assert next(i for i in inv if not i["flagged"])["selected_by_default"] is True


def test_approval_rules(api, smtp):
    client, _ = api
    cid, _ = run_case(client)
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": []}).status_code == 422
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": ["Enope"]}).status_code == 422
    assert client.post("/customer/cases/nope/approve-outreach", json={"refs": ["E1"]}).status_code == 404
    assert smtp.sent == []
    refs = refs_of(client, cid)
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs}).status_code == 200
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs}).status_code == 409   # one send per email
    assert len(smtp.sent) == 1


def test_case_still_planned_cannot_send_invitations(api, smtp):
    client, _ = api
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": ["E1"]}).status_code == 409


def test_operators_no_longer_approve_or_reject_emails(api, smtp):
    client, _ = api
    _, items = run_case(client)
    for action in ("approve", "reject"):
        assert client.post(f"/approvals/{items[0]['id']}/{action}", json={"approver": "dev"}).status_code in (404, 405)
    assert smtp.sent == [] and client.get("/approvals").json()[0]["status"] == "DRAFTED"


def test_allowlist_blocks_any_other_address_and_records_it(api, smtp):
    client, _ = api
    conn = db.connect()
    queue.create_draft(conn, case_id="c1", person_id=5, name="X Y", persona_title="t", persona_company="c", tenure_months=12,
                       subquestion_indices=[1], flags=[], to_address="stranger@example.com", subject="s",
                       body_template="Hello {{first_name}} {{link}}", link_base="http://x", llm_call_id=None)
    from app.jobs.views import expert_ref
    r = queue.approve_batch(conn, "c1", [expert_ref("c1", 5)])
    assert r == {"sent": 0, "dropped": 0, "blocked": 1, "failed": 0}
    row = conn.execute("SELECT * FROM outreach").fetchone()
    assert row["status"] == "BLOCKED" and "allowlist" in row["block_reason"]
    assert smtp.sent == []
    assert conn.execute("SELECT COUNT(*) c FROM events WHERE type='mail.blocked'").fetchone()["c"] == 1
    assert verify_chain(conn) == (True, None)


def test_send_mail_itself_refuses_without_going_through_the_queue(smtp):
    with pytest.raises(mail.MailBlocked):
        mail.send_mail("stranger@example.com", "s", "b")
    assert smtp.sent == []


def test_mail_failure_is_recorded_not_hidden(api, smtp):
    client, _ = api
    cid, _ = run_case(client)
    smtp.fail = True
    r = client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs_of(client, cid)}).json()
    assert r["failed"] == 1 and r["state"] == "AWAITING_APPROVAL"
    row = client.get("/approvals", params={"case_id": cid}).json()[0]
    assert row["status"] == "FAILED" and "mailpit is not running" in row["block_reason"]


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
