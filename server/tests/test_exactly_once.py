"""Kill-and-restart behaviour of invitation sends: each email is sent exactly once."""
import json

import pytest

from app.actions import mail, queue
from app.core import db
from app.jobs import runner
from tests.test_outreach import FakeSMTP, smtp  # noqa: F401  (fixture)
from tests.test_runner import api, start  # noqa: F401  (fixtures and helpers)


class Killed(BaseException):
    """Stands in for kill -9: not an Exception, so nothing in the service can catch it."""


def approved_case(client):
    cid = start(client)
    refs = [i["ref"] for i in client.get(f"/customer/cases/{cid}").json()["invites"]]
    return cid, refs


def test_kill_after_the_mail_server_accepted_does_not_send_twice(api, smtp, monkeypatch):
    client, _ = api
    cid, refs = approved_case(client)
    real = FakeSMTP.send_message

    def accept_then_die(self, msg):
        real(self, msg)            # the mail server has the message...
        raise Killed()             # ...and the process dies before the database records it

    monkeypatch.setattr(FakeSMTP, "send_message", accept_then_die)
    with pytest.raises(Killed):
        queue.approve_batch(db.connect(), cid, refs)
    conn = db.connect()
    assert conn.execute("SELECT status FROM actions").fetchone()["status"] == "PENDING"
    assert conn.execute("SELECT status FROM outreach").fetchone()["status"] == "APPROVED"
    # restart: the mailbox already holds the message with this key, so nothing is sent again
    monkeypatch.setattr(FakeSMTP, "send_message", real)
    key = queue.action_key(cid, "send_invitation", conn.execute("SELECT id FROM outreach").fetchone()["id"])
    assert smtp.sent[0]["Message-ID"] == f"<{key}@synex.local>"
    monkeypatch.setattr(queue, "_in_mailbox", lambda k: k == key)
    runner.resume_on_startup()
    assert len(smtp.sent) == 1
    assert conn.execute("SELECT status FROM outreach").fetchone()["status"] == "SENT"
    assert conn.execute("SELECT status FROM actions").fetchone()["status"] == "DONE"
    assert client.get(f"/cases/{cid}").json()["state"] == "COLLECTING"


def test_kill_before_the_send_sends_once_on_restart(api, smtp, monkeypatch):
    client, _ = api
    cid, refs = approved_case(client)
    real_send = mail.send_mail

    def die(*a, **k):
        raise Killed()

    monkeypatch.setattr(mail, "send_mail", die)
    with pytest.raises(Killed):
        queue.approve_batch(db.connect(), cid, refs)
    assert smtp.sent == []
    monkeypatch.setattr(mail, "send_mail", real_send)        # restart with the real code
    monkeypatch.setattr(queue, "_in_mailbox", lambda k: False)
    runner.resume_on_startup()
    runner.resume_on_startup()                               # a second restart changes nothing
    assert len(smtp.sent) == 1


def test_unknown_outcome_is_never_resent(api, smtp, monkeypatch):
    client, _ = api
    cid, refs = approved_case(client)
    monkeypatch.setattr(mail, "send_mail", lambda *a, **k: (_ for _ in ()).throw(Killed()))
    with pytest.raises(Killed):
        queue.approve_batch(db.connect(), cid, refs)
    monkeypatch.setattr(queue, "_in_mailbox", lambda k: None)   # mailbox unreachable after the restart
    sends = []
    monkeypatch.setattr(mail, "send_mail", lambda *a, **k: sends.append(1))
    runner.resume_on_startup()
    row = db.connect().execute("SELECT status, block_reason FROM outreach").fetchone()
    assert sends == [] and row["status"] == "FAILED" and "not sent again" in row["block_reason"]


def test_a_done_action_is_never_repeated(api, smtp):
    client, _ = api
    cid, refs = approved_case(client)
    client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs})
    conn = db.connect()
    row = conn.execute("SELECT * FROM outreach").fetchone()
    queue._send(conn, row, "customer")                       # a bug or a replay calls send again
    assert len(smtp.sent) == 1


def test_stale_sourcing_case_without_plan_approval_is_failed_on_startup(api):
    client, _ = api
    conn = db.connect()
    cid = runner.create_case(conn, "What does Acme do?")
    runner.set_state(conn, cid, "SOURCING")
    runner.resume_on_startup()
    assert client.get(f"/cases/{cid}").json()["state"] == "FAILED"
    reasons = [json.loads(r["payload"]) for r in conn.execute("SELECT payload FROM events WHERE case_id=? AND type='case.state'", (cid,))]
    assert reasons[-1] == {"state": "FAILED", "reason": "pre-stage-6 dev run"}
