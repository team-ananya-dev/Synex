"""Expert page API (Ananya). Reuses Dev's fixtures: a fake Crustdata, a fake model and a fake SMTP."""
import pytest

from app.core import db
from app.main import app
from app.routes.expert import ATTESTATIONS, router as expert_router
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_runner import api, db_events, start  # noqa: F401  (fixtures and helpers)

# main.py (Dev's) may not register the expert router yet; mount it once for the tests
if not any(getattr(r, "path", "") == "/expert/{token}" for r in app.routes):
    app.include_router(expert_router)

ALL_TICKED = {a: True for a in ATTESTATIONS}


def _token(outreach_id):
    return db.connect().execute("SELECT token FROM outreach WHERE id=?", (outreach_id,)).fetchone()["token"]


@pytest.fixture
def sent(api, smtp):
    """A case whose one draft was approved and sent. Returns (client, case_id, token, sub-question indices)."""
    client, _ = api
    cid = start(client)
    item = client.get("/approvals", params={"case_id": cid}).json()[0]
    refs = [i["ref"] for i in client.get(f"/customer/cases/{cid}").json()["invites"]]
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs}).json()["sent"] == 1
    return client, cid, _token(item["id"]), item["subquestion_indices"]


def _answers(indices):
    return [{"index": i, "kind": "answer", "text": f"first-hand answer {i}", "confidence": "medium"} for i in indices]


def test_page_shows_persona_and_subquestions_but_no_customer(sent):
    client, cid, token, indices = sent
    page = client.get(f"/expert/{token}").json()
    assert page["available"] and not page["submitted"]
    assert [s["index"] for s in page["subquestions"]] == indices
    assert page["payout"]["currency"].endswith("(simulated)")
    assert "case_id" not in page and "question" not in page and "to_address" not in str(page)


def test_unknown_token_is_404_and_unsent_link_is_closed(api, smtp):
    client, _ = api
    assert client.get("/expert/nope").status_code == 404
    cid = start(client)
    item = client.get("/approvals", params={"case_id": cid}).json()[0]   # still DRAFTED
    token = _token(item["id"])
    assert client.get(f"/expert/{token}").json() == {"available": False, "reason": "This invitation is not active."}
    r = client.post(f"/expert/{token}/responses", json={"attestations": ALL_TICKED, "answers": _answers(item["subquestion_indices"])})
    assert r.status_code == 409


def test_submit_stores_append_only_rows_and_moves_case_to_collecting(sent):
    client, cid, token, indices = sent
    r = client.post(f"/expert/{token}/responses", json={"attestations": ALL_TICKED, "answers": _answers(indices)})
    assert r.status_code == 201, r.text
    got = r.json()["received"]
    assert [g["subquestion_index"] for g in got] == indices and all(g["response_id"].startswith("R") for g in got)
    conn = db.connect()
    rows = conn.execute("SELECT * FROM responses WHERE case_id=?", (cid,)).fetchall()
    assert len(rows) == len(indices) and rows[0]["mode"] == "form"
    with pytest.raises(Exception):
        conn.execute("UPDATE responses SET text='edited'")
    evs = db_events(cid)
    received = [e for e in evs if e["type"] == "response.received"]
    assert len(received) == len(indices) and all("text" not in e for e in received)
    assert {"type": "case.state", "state": "COLLECTING"} in [{"type": e["type"], "state": e.get("state")} for e in evs]
    assert client.get(f"/expert/{token}").json()["submitted"] is True
    again = client.post(f"/expert/{token}/responses", json={"attestations": ALL_TICKED, "answers": _answers(indices)})
    assert again.status_code == 409                                      # one submission per link


def test_submission_rules(sent):
    client, _, token, indices = sent
    post = lambda body: client.post(f"/expert/{token}/responses", json=body)  # noqa: E731
    assert post({"attestations": {**ALL_TICKED, "no_confidential_info": False}, "answers": _answers(indices)}).status_code == 422
    assert post({"attestations": ALL_TICKED, "answers": _answers(indices[:-1])}).status_code == 422       # one missing
    assert post({"attestations": ALL_TICKED, "answers": _answers(indices + [99])}).status_code == 422     # one extra
    bad = _answers(indices)
    bad[0]["text"] = " "
    assert post({"attestations": ALL_TICKED, "answers": bad}).status_code == 422                           # empty answer
    ok = [{"index": i, "kind": "confidential", "text": "ignored"} for i in indices]
    r = post({"attestations": ALL_TICKED, "answers": ok})
    assert r.status_code == 201
    assert db.connect().execute("SELECT text FROM responses WHERE kind='confidential'").fetchone()["text"] == ""
