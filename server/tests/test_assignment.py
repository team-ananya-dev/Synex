"""Several questions per expert (Ananya): each invited expert gets a fixed small number of questions."""
from types import SimpleNamespace

import pytest

from app import question_assignment as qa
from app.core import db
from tests.test_expert import sent  # noqa: F401  (fixture)
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_runner import api, db_events  # noqa: F401  (fixtures and helpers)

SUBS = [{"index": i, "text": f"Question {i}?", "expertise": "ops"} for i in (1, 2, 3, 4)]


def person(pid, **kw):
    return {"person_id": pid, "title": "Operations Manager", "function": "Operations", "tenure_months": 24,
            "reason": "ops role", "role_description": None, "skills": [], **kw}


def chosen_for(primaries: dict[int, list[int]]):
    return {pid: {"person": person(pid), "subs": [SUBS[i - 1] for i in idx]} for pid, idx in primaries.items()}


class FakeClient:
    """Answers the assignment call with a scripted reply; anything else is not expected."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls += 1
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=reply, id="t")],
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20))


@pytest.fixture
def conn(monkeypatch, tmp_path):
    monkeypatch.setenv("SYNEX_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("SYNEX_ANTHROPIC_KEY", "test")
    return db.connect()


def run(conn, chosen, replies, panels=None, k=3):
    fake = FakeClient(replies)
    import anthropic
    orig = anthropic.Anthropic
    anthropic.Anthropic = lambda **kw: fake
    try:
        return qa.assign(conn, "c1", chosen, SUBS, panels or {}, k), fake
    finally:
        anthropic.Anthropic = orig


def test_model_preferences_are_used_in_order_and_primary_stays_first(conn):
    chosen = chosen_for({10: [1], 11: [2]})
    reply = {"assignments": [{"person_id": 10, "subquestions": [1, 4, 3, 2]}, {"person_id": 11, "subquestions": [3, 1]}]}
    method, _ = run(conn, chosen, [reply])
    assert method == "model"
    assert [s["index"] for s in chosen[10]["subs"]] == [1, 4, 3]       # primary first, then the model's best two (k = 3)
    assert [s["index"] for s in chosen[11]["subs"]] == [2, 3, 1]
    ev = [e for e in db_events("c1") if e["type"] == "questions.assigned"][0]
    assert ev["questions_per_expert"] == 3 and ev["method"] == "model" and ev["questions_total"] == 6
    assert "person_id" not in ev                                        # no personal data in the event


def test_count_is_fixed_by_code_when_the_model_gives_too_few(conn):
    chosen = chosen_for({10: [1], 11: [2]})
    reply = {"assignments": [{"person_id": 10, "subquestions": [1]}, {"person_id": 11, "subquestions": [2, 4]}]}   # lazy reply
    method, _ = run(conn, chosen, [reply])
    assert method == "model+rule"
    assert all(len(e["subs"]) == 3 for e in chosen.values())
    assert [s["index"] for s in chosen[11]["subs"]][:2] == [2, 4]       # the model's pick kept, the rest filled by rule


def test_malformed_model_reply_falls_back_to_the_rule_and_still_gives_k(conn):
    chosen = chosen_for({10: [1], 11: [2]})
    bad = {"assignments": [{"person_id": 10, "subquestions": [1, 99]}]}   # a sub-question that does not exist
    method, fake = run(conn, chosen, [bad])
    assert method == "rule" and fake.calls == 2                         # one retry, then the rule
    assert all(len(e["subs"]) == 3 for e in chosen.values())
    assert [s["index"] for s in chosen[10]["subs"]][0] == 1 and [s["index"] for s in chosen[11]["subs"]][0] == 2


def test_rule_prefers_the_sub_question_where_the_expert_ranked_best():
    panels = {"3": [{"person_id": 10, "score": 90}], "4": [{"person_id": 10, "score": 40}], "2": [{"person_id": 10, "score": 60}]}
    assert qa.fallback_extras(10, [1], [1, 2, 3, 4], 3, panels) == [3, 2]
    assert qa.fallback_extras(10, [1], [1, 2, 3, 4], 2, {}) == [2]        # nothing ranked: plan order
    assert qa.fallback_extras(10, [1, 3], [1, 2, 3, 4], 3, panels) == [2]  # only as many as still needed


def test_never_more_than_the_plan_has_and_one_question_means_no_change(conn):
    two = [SUBS[0], SUBS[1]]
    chosen = {10: {"person": person(10), "subs": [SUBS[0]]}}
    import anthropic
    orig, fake = anthropic.Anthropic, FakeClient([{"assignments": [{"person_id": 10, "subquestions": [1, 2]}]}])
    anthropic.Anthropic = lambda **kw: fake
    try:
        assert qa.assign(conn, "c1", chosen, two, {}, 3) == "model"      # k capped at 2 questions in the plan
    finally:
        anthropic.Anthropic = orig
    assert len(chosen[10]["subs"]) == 2
    one = chosen_for({10: [1]})
    assert qa.assign(conn, "c1", one, SUBS, {}, 1) == "none" and len(one[10]["subs"]) == 1


def test_expert_with_many_primaries_keeps_them_all(conn):
    chosen = chosen_for({10: [1, 2, 3, 4], 11: [1]})
    reply = {"assignments": [{"person_id": 10, "subquestions": [1, 2, 3, 4]}, {"person_id": 11, "subquestions": [1, 2, 3]}]}
    method, _ = run(conn, chosen, [reply])
    assert method == "model" and len(chosen[10]["subs"]) == 4 and len(chosen[11]["subs"]) == 3


def test_setting_is_bounded(monkeypatch):
    monkeypatch.setenv("SYNEX_QUESTIONS_PER_EXPERT", "99")
    assert qa.questions_per_expert() == qa.MAX_PER_EXPERT
    monkeypatch.setenv("SYNEX_QUESTIONS_PER_EXPERT", "x")
    assert qa.questions_per_expert() == 3
    monkeypatch.delenv("SYNEX_QUESTIONS_PER_EXPERT")
    assert qa.questions_per_expert() == 3


def test_full_flow_gives_every_expert_more_than_one_question(api, sent):
    """Through the real runner with Dev's fake model: the assignment call is invalid there, so the rule fills in."""
    client, cid, token, indices = sent
    page = client.get(f"/expert/{token}").json()
    assert len(page["subquestions"]) == len(indices) >= 2
