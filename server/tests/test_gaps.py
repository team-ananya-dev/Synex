"""Gap fixes after the first full run (Ananya): named companies survive the question screen, coarse role labels,
closing a case, experts told their screening result, honest agreement labels, unsourced sub-questions."""
from app.anonymity import anonymise_roles, coarse_role
from app.core import llm
from app.stages import s1_question_screen as s1
from app.stages import s8_result
from tests.test_expert import ALL_TICKED, sent  # noqa: F401  (fixture)
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_response_screen import script, submit
from tests.test_runner import api, db_events  # noqa: F401  (fixtures and helpers)


def _s1_reply(monkeypatch, reply):
    monkeypatch.setattr(llm, "call_json", lambda conn, **kw: (reply, "call"))


def test_rewrite_that_drops_a_named_company_gets_it_back(monkeypatch):
    q = "How has demand changed at Acme Coffee Roasters over two years?"
    _s1_reply(monkeypatch, {"verdict": "rewrite", "reason": "r", "rewritten_question": "How has coffee demand changed?",
                            "named_companies": ["Acme Coffee Roasters", "Ghost Corp"]})
    out, _ = s1.screen(None, q, None)
    assert "Acme Coffee Roasters" in out["effective_question"]
    assert out["named_companies"] == ["Acme Coffee Roasters"]          # a name not in the question is ignored
    assert out["restored_companies"] == ["Acme Coffee Roasters"]


def test_allowed_question_is_unchanged_and_rewrite_that_keeps_names_is_untouched(monkeypatch):
    _s1_reply(monkeypatch, {"verdict": "allow", "reason": "r", "rewritten_question": "", "named_companies": ["Acme"]})
    assert s1.screen(None, "What happened at Acme?", None)[0]["effective_question"] == "What happened at Acme?"
    _s1_reply(monkeypatch, {"verdict": "rewrite", "reason": "r", "rewritten_question": "How did Acme grow?", "named_companies": ["Acme"]})
    out, _ = s1.screen(None, "Leak Acme's numbers?", None)
    assert out["effective_question"] == "How did Acme grow?" and out["restored_companies"] == []
    _s1_reply(monkeypatch, {"verdict": "allow", "reason": "r", "rewritten_question": ""})   # older reply shape still works
    assert s1.screen(None, "What happened at Acme?", None)[0]["named_companies"] == []


def test_coarse_role_labels():
    assert coarse_role("Regional Manager Operations & Sales") == "Sales manager"
    assert coarse_role("ASM") == "Sales manager"
    assert coarse_role("VP Supply Chain") == "Senior supply chain leader"
    assert coarse_role("Store Manager") == "Store operations manager"
    assert coarse_role("Business & Pricing Analyst") == "Strategy specialist"
    assert coarse_role(None) == "Former employee"


def test_title_shared_by_three_experts_stays_exact_otherwise_coarse():
    answers = [{"person_id": i, "role": "Store Manager"} for i in range(3)] + [{"person_id": 9, "role": "Head of Growth"}]
    anonymise_roles(answers)
    assert [a["role"] for a in answers[:3]] == ["Store Manager"] * 3
    assert answers[3]["role"] == "Senior marketing leader"
    same_person_twice = [{"person_id": 1, "role": "Store Manager"}, {"person_id": 1, "role": "Store Manager"}]
    anonymise_roles(same_person_twice)                                   # one person counted once
    assert same_person_twice[0]["role"] == "Store operations manager"


def test_customer_sees_coarse_role_on_answers(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "accepted", "reason": "fine", "flagged_spans": []})
    submit(client, token, indices, ["Teams grew steadily over two years."] * len(indices))
    shown = client.get(f"/customer/cases/{cid}/responses").json()["responses"]
    assert shown and all(r["role"] != "Operations Manager" for r in shown)    # exact title of a single expert hidden
    assert all("person_id" not in r for r in shown)
    result = client.get(f"/customer/cases/{cid}/result").json()
    assert all(a["role"] != "Operations Manager" for sq in result["subquestions"] for a in sq["answers"])


def test_close_case_needs_an_accepted_answer_then_stops_new_answers(api, sent):
    client, cid, token, indices = sent
    assert client.post(f"/customer/cases/{cid}/close").status_code == 409            # nothing accepted yet
    script(api, {"verdict": "accepted", "reason": "fine", "flagged_spans": []})
    submit(client, token, indices, ["Teams grew steadily over two years."] * len(indices))
    r = client.post(f"/customer/cases/{cid}/close")
    assert r.status_code == 200 and r.json()["state"] == "DELIVERED"
    assert client.get(f"/customer/cases/{cid}").json()["state"] == "DELIVERED"
    assert {"type": "case.state", "state": "DELIVERED"} in [{"type": e["type"], "state": e.get("state")} for e in db_events(cid)]
    assert client.post(f"/customer/cases/{cid}/close").status_code == 409            # only once
    assert client.get("/customer/cases/nope/close").status_code in (404, 405)
    assert client.get(f"/expert/{token}").json()["submitted"] is True                 # the expert still sees the outcome


def test_expert_is_told_the_result_of_each_answer(api, sent):
    client, _, token, indices = sent
    script(api, {"verdict": "redacted", "reason": "an exact internal figure", "flagged_spans": ["margin was 4.2%"]})
    submit(client, token, indices, ["Costs fell; the margin was 4.2% last quarter."] * len(indices))
    page = client.get(f"/expert/{token}").json()
    assert [s["index"] for s in page["screening"]] == indices
    first = page["screening"][0]
    assert first["verdict"] == "redacted" and first["reason"] == "an exact internal figure" and first["removed"] == ["margin was 4.2%"]


def test_different_aspects_is_not_reported_as_split():
    result = {"summary_status": "not written", "subquestions": [
        {"index": 1, "independent_sources": 2, "label": "multiple sources, agreement not assessed", "label_basis": "code", "summary": None}]}
    summary = {"fingerprint": "f", "llm_call_id": "c",
               "subquestions": {"1": {"agreement": "different aspects", "sentences": [], "dropped_uncited": 0}}}
    out = s8_result._attach(result, summary, "f")
    assert out["subquestions"][0]["label"] == "multiple sources, different aspects"
    assert out["subquestions"][0]["label_basis"] == "model"


def test_panel_is_spread_across_companies_before_a_second_person_from_one():
    from app.stages.s6_outreach_writer import spread_by_company
    panel = [{"person_id": i, "company_id": c} for i, c in [(1, "A"), (2, "A"), (3, "A"), (4, "B"), (5, "C"), (6, "B")]]
    assert [p["person_id"] for p in spread_by_company(panel, 3)] == [1, 4, 5]          # one per company
    assert [p["person_id"] for p in spread_by_company(panel, 5)] == [1, 4, 5, 2, 6]    # then second picks, best first
    assert [p["person_id"] for p in spread_by_company(panel, 10)] == [1, 4, 5, 2, 6, 3]
    only_a = [{"person_id": i, "company_id": "A"} for i in range(4)]
    assert [p["person_id"] for p in spread_by_company(only_a, 2)] == [0, 1]            # one company: plain top 2
    assert spread_by_company([], 3) == []


def test_company_picker_treats_the_question_as_background_and_never_overrides_the_model(monkeypatch):
    """A peer company must not be judged against the question (that made every competitor 'not confident'), and the
    model's own 'unsure' is respected: the runner reports it as ambiguous instead of guessing."""
    from app.stages import s3_sourcer
    seen = {}
    cands = [{"company_id": i, "name": n, "domain": d, "year_founded": 2000, "size": "1001-5000", "industries": [], "description": "", "confidence": 1}
             for i, (n, d) in enumerate([("Delhivery", "delhivery.com"), ("Delhivery courier", None)], start=1)]
    monkeypatch.setattr(s3_sourcer.company_api, "identify", lambda client, name: (cands, "call"))

    def fake(conn, **kw):
        seen.update(kw)
        return {"company_id": 1, "reason": "r", "confident": seen.get("answer_confident", True)}, "llm1"
    monkeypatch.setattr(s3_sourcer.llm, "call_json", fake)
    chosen, _, pick = s3_sourcer.resolve_company(None, None, "Delhivery", "How does Xpressbees run its hubs?", "c1")
    assert "Company to find: Delhivery" in seen["user"] and "do not match against it" in seen["user"]
    assert "never reject a record because the question" in seen["system"]
    assert chosen["name"] == "Delhivery" and pick["confident"] is True and pick["method"] == "model"
    seen["answer_confident"] = False
    chosen, _, pick = s3_sourcer.resolve_company(None, None, "Apollo", "x", "c1")
    assert pick["confident"] is False and pick["method"] == "model"       # no code override of the model's doubt
