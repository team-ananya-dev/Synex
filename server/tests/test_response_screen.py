"""Stage 7 response screen (Ananya). Reuses Dev's fixtures; the model's screen reply is scripted per test."""
from types import SimpleNamespace

import pytest

from app.core import db
from app.stages import s7_response_screen as s7
from tests.test_expert import ALL_TICKED, sent  # noqa: F401  (fixture)
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_runner import api, db_events  # noqa: F401  (fixtures and helpers)


class ScreenFake:
    """Answers the response screen with scripted replies (one per call); other stages go to Dev's fake."""
    def __init__(self, base, *replies):
        self.base, self.replies, self.calls = base, list(replies), 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        if "flagged_spans" not in kw["tools"][0]["input_schema"]["properties"]:
            return self.base.messages.create(**kw)
        self.calls += 1
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=reply, id="t")],
                               usage=SimpleNamespace(input_tokens=200, output_tokens=30))


def script(api, *replies):
    _, fake = api
    fake["v"] = ScreenFake(fake["v"], *replies)
    return fake["v"]


def submit(client, token, indices, texts):
    answers = [{"index": i, "kind": "answer", "text": t, "confidence": "medium"} for i, t in zip(indices, texts)]
    r = client.post(f"/expert/{token}/responses", json={"attestations": ALL_TICKED, "answers": answers})
    assert r.status_code == 201, r.text
    return [g["response_id"] for g in r.json()["received"]]


def latest(rid):
    return s7.latest(db.connect(), rid)


def test_accepted_answer_reaches_the_customer_with_an_anonymous_ref(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "accepted", "reason": "general first-hand experience", "flagged_spans": []})
    rids = submit(client, token, indices, [f"Ops teams grew steadily, roughly doubling over two years ({i})" for i in indices])
    assert all(latest(r)["verdict"] == "accepted" for r in rids)
    view = client.get(f"/customer/cases/{cid}/responses").json()
    assert view["coverage"][str(indices[0])]["accepted"] == 1
    shown = view["responses"][0]
    assert shown["ref"].startswith("E") and "roughly doubling" in shown["text"]
    assert "Quentin" not in str(view) and "person_id" not in shown and "outreach_id" not in shown
    screened = [e for e in db_events(cid) if e["type"] == "response.screened"]
    assert len(screened) == len(indices) and all("reason" not in e and "text" not in e for e in screened)


def test_redaction_removes_only_verified_spans(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "redacted", "reason": "contains an exact internal figure", "flagged_spans": ["margin was 4.2%"]})
    rids = submit(client, token, indices, ["Costs fell; the margin was 4.2% last quarter and improving."] * len(indices))
    row = latest(rids[0])
    assert row["verdict"] == "redacted" and row["redacted_text"] == "Costs fell; the [redacted] last quarter and improving."
    assert "4.2%" not in str(client.get(f"/customer/cases/{cid}/responses").json())


def test_span_not_in_the_answer_is_sent_back_then_held(api, sent):
    client, _, token, indices = sent
    fake = script(api, {"verdict": "redacted", "reason": "figure", "flagged_spans": ["words the expert never wrote"]})
    rids = submit(client, token, indices, ["Costs fell over time."] * len(indices))
    row = latest(rids[0])
    assert row["verdict"] == "held" and "could not be verified" in row["reason"]
    assert fake.calls == 2 * len(indices)                        # one retry per answer, then held, never accepted


def test_code_rule_holds_a_leak_phrase_the_model_accepted(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "accepted", "reason": "fine", "flagged_spans": []})
    rids = submit(client, token, indices, ["I shouldn't say this, but the internal deck showed a big loss."] * len(indices))
    row = latest(rids[0])
    assert row["verdict"] == "held" and "code rule" in row["reason"]
    assert client.get(f"/customer/cases/{cid}/responses").json()["responses"] == []      # held text never shown


def test_dont_know_needs_no_model_call(api, sent):
    client, _, token, indices = sent
    fake = script(api, {"verdict": "accepted", "reason": "x", "flagged_spans": []})
    answers = [{"index": i, "kind": "dont_know"} for i in indices]
    rids = [g["response_id"] for g in client.post(f"/expert/{token}/responses",
            json={"attestations": ALL_TICKED, "answers": answers}).json()["received"]]
    assert fake.calls == 0 and latest(rids[0])["verdict"] == "rejected" and "do not know" in latest(rids[0])["reason"]


def test_team_member_reviews_a_held_answer_without_editing_it(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "held", "reason": "unsure whether a figure is public", "flagged_spans": []})
    rids = submit(client, token, indices, ["Delivery times were about 20 minutes in big cities."] * len(indices))
    held = client.get("/operator/responses", params={"status": "held", "case_id": cid}).json()
    assert {h["response_id"] for h in held} == set(rids) and held[0]["text"].startswith("Delivery times")
    post = lambda rid, who, d: client.post(f"/operator/responses/{rid}/decide", json={"approver": who, "decision": d})  # noqa: E731
    assert post(rids[0], "customer", "accept").status_code == 403         # only registered team members
    assert post(rids[0], "ananya", "accept").json()["verdict"] == "accepted"
    assert post(rids[0], "dev", "reject").status_code == 409              # already decided
    assert latest(rids[0])["decided_by"] == "ananya"
    shown = client.get(f"/customer/cases/{cid}/responses").json()["responses"]
    assert [s["response_id"] for s in shown] == [rids[0]]
    with pytest.raises(Exception):
        db.connect().execute("UPDATE response_screens SET verdict='accepted'")


def test_redact_helper_tolerates_whitespace():
    assert s7.redact("a  b\nc d", ["b c"]) == "a  [redacted] d"
