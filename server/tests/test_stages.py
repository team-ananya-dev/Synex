from datetime import date
from types import SimpleNamespace

import pytest

from app.core import db, llm
from app.stages import s3_sourcer, s4_people_screen, s5_ranker

TODAY = date(2026, 11, 22)
PARAMS = {"min_left": 6, "max_left": 24, "min_years": 1, "competitor_domains": ["rival.com", "quickmart.in"]}


def cand(**kw):
    base = {"person_id": 1, "name": "A B", "title": "Operations Manager", "function": None, "headline": "",
            "start_date": "2023-01-01", "end_date": "2025-06-01", "tenure_months": 29, "still_at_company": False,
            "current_employers": []}
    return {**base, **kw}


def test_screen_passes_and_explains():
    s = s4_people_screen.screen(cand(), TODAY, PARAMS)
    assert s["verdict"] == "pass" and all(r["reason"] for r in s["results"])


@pytest.mark.parametrize("kw,rule", [
    ({"still_at_company": True}, "rule_not_current"),
    ({"end_date": "2026-09-01"}, "rule_cooling_off"),
    ({"end_date": "2023-01-01"}, "rule_freshness"),
    ({"tenure_months": 5}, "rule_min_tenure"),
])
def test_screen_fails_each_rule(kw, rule):
    s = s4_people_screen.screen(cand(**kw), TODAY, PARAMS)
    assert s["verdict"] == "fail"
    assert [r["rule"] for r in s["results"] if not r["passed"]] == [rule]


def role(**kw):
    return {"company_id": "9", "name": "Rival", "website": "https://www.rival.com/", "title": "Dispatcher", "seniority": "Entry Level", **kw}


def test_rule4_sensitive_role_at_competitor_fails():
    s = s4_people_screen.screen(cand(current_roles=[role(title="Operations Manager", seniority="Director")]), TODAY, PARAMS)
    assert s["verdict"] == "fail"
    assert [r["rule"] for r in s["results"] if not r["passed"]] == ["rule_competitor"]
    assert "direct competitor" in s["results"][4]["reason"]


def test_rule4_strategic_title_counts_as_sensitive_even_at_low_seniority():
    c = cand(current_roles=[role(title="Pricing Analyst", seniority="Entry Level")])
    assert s4_people_screen.screen(c, TODAY, PARAMS)["verdict"] == "fail"


def test_rule4_lesser_role_at_competitor_is_a_review_flag():
    s = s4_people_screen.screen(cand(current_roles=[role()]), TODAY, PARAMS)
    assert s["verdict"] == "review" and s["results"][-1]["flag"] and "non-sensitive" in s["results"][-1]["reason"]


def test_rule4_matches_employer_by_name_when_domains_differ():
    c = cand(current_roles=[role(name="Quickmart", website="https://www.parent-group.example/", title="Store Manager", seniority="Experienced Manager")])
    assert s4_people_screen.screen(c, TODAY, PARAMS)["verdict"] == "fail"


def test_rule4_unrelated_employer_passes():
    c = cand(current_roles=[role(name="Acme Corp", website="https://acme.com")])
    assert s4_people_screen.screen(c, TODAY, PARAMS)["verdict"] == "pass"


def test_rule4_unavailable_competitor_list_is_never_a_silent_pass():
    s = s4_people_screen.screen(cand(), TODAY, {**PARAMS, "competitor_domains": None})
    assert s["verdict"] == "review" and "could not be fetched" in s["results"][-1]["reason"]


def test_sensitive_role_is_flagged_not_failed():
    assert s4_people_screen.screen(cand(title="Chief Operating Officer"), TODAY, PARAMS)["verdict"] == "review"


def test_normalise_uses_target_company_role_only():
    profile = {"crustdata_person_id": 7, "basic_profile": {"name": "X"}, "metadata": {},
               "experience": {"employment_details": {
                   "past": [{"crustdata_company_id": 1, "end_date": "2025-01-01T00:00:00", "start_date": "2023-01-01T00:00:00", "title": "Other"},
                            {"crustdata_company_id": 2, "end_date": "2025-06-01T00:00:00", "start_date": "2023-06-01T00:00:00", "title": "Target"}],
                   "current": [{"crustdata_company_id": 3, "name": "Else"}]}}}
    c = s3_sourcer.normalise(profile, 2, "call", TODAY)
    assert c["title"] == "Target" and c["tenure_months"] == 24 and not c["still_at_company"]


class FakeAnthropic:
    """Returns queued tool replies; no network."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        block = SimpleNamespace(type="tool_use", input=self.replies.pop(0), id="t1")
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def _rank_with(conn, replies, cands):
    import os
    fake = FakeAnthropic(replies)
    orig = llm.anthropic.Anthropic
    llm.anthropic.Anthropic = lambda **k: fake
    try:
        os.environ["SYNEX_ANTHROPIC_KEY"] = "test"
        return s5_ranker.rank(conn, cands, "q", "ops", "c1")
    finally:
        llm.anthropic.Anthropic = orig


def entry(pid, score, evidence, conflict=""):
    return {"person_id": pid, "score": score, "evidence": evidence, "reason": "r", "data_conflict": conflict}


def test_ranker_retries_once_on_invalid_reply_and_logs_both():
    conn = db.connect(":memory:")
    result, _ = _rank_with(conn, [{"ranked": [entry(99, 5, [])]}, {"ranked": [entry(1, 70, ["Operations Manager"])]}], [cand()])
    assert result["ranked"][0]["score"] == 70 and result["ranked"][0]["fit"] == "strong"
    rows = conn.execute("SELECT attempt, valid FROM llm_calls ORDER BY id").fetchall()
    assert [(r["attempt"], r["valid"]) for r in rows] == [(1, 0), (2, 1)]
    assert llm.spent_usd(conn) > 0


def test_unsupported_evidence_is_dropped_and_caps_the_score():
    conn = db.connect(":memory:")
    cands = [cand(person_id=1), cand(person_id=2, title="Analyst")]
    result, _ = _rank_with(conn, [{"ranked": [
        entry(1, 90, ["Operations Manager", "ran 40 dark stores"]),   # one real snippet, one invented
        entry(2, 90, ["Head of Rider Fleet"]),                        # nothing verifiable
    ]}], cands)
    assert [r["person_id"] for r in result["ranked"]] == [1]
    assert result["ranked"][0]["evidence"] == ["Operations Manager"] and result["ranked"][0]["evidence_dropped"] == 1
    assert result["excluded"][0]["person_id"] == 2 and result["excluded"][0]["why"] == "no supported evidence"
    assert result["excluded"][0]["score"] == s5_ranker.UNSUPPORTED_CAP


def test_tenure_and_labels_are_not_evidence():
    conn = db.connect(":memory:")
    result, _ = _rank_with(conn, [{"ranked": [entry(1, 90, ["tenure: 29 months", "title: Operations Manager", "Bengaluru"])]}], [cand()])
    assert result["ranked"] == [] and result["excluded"][0]["why"] == "no supported evidence"


def test_low_fit_is_left_off_the_panel():
    conn = db.connect(":memory:")
    result, _ = _rank_with(conn, [{"ranked": [entry(1, 20, ["Operations Manager"])]}], [cand()])
    assert result["ranked"] == [] and result["excluded"][0]["why"] == "low fit"


def test_with_profile_adds_role_description_and_skills_for_target_company_only():
    person_data = {"experience": {"employment_details": {"past": [
        {"crustdata_company_id": 5, "description": "other job", "end_date": "2024-01-01"},
        {"crustdata_company_id": 9, "description": " Ran rider allocation ", "end_date": "2025-01-01"}]}},
        "skills": {"professional_network_skills": ["Logistics"]}}
    c = s5_ranker.with_profile(cand(), person_data, 9)
    assert c["role_description"] == "Ran rider allocation" and c["skills"] == ["Logistics"]
    assert "role description: Ran rider allocation" in s5_ranker.facts_for(c)


def test_budget_blocks_calls(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setattr(llm, "BUDGET_USD", 0.0)
    with pytest.raises(llm.BudgetExceeded):
        llm.call_json(conn, purpose="t", system="s", user="u", schema={"type": "object"}, client=FakeAnthropic([{}]))


def test_ranker_scores_in_batches_and_caps_how_many_it_scores(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setattr(s5_ranker, "BATCH", 2)
    monkeypatch.setattr(s5_ranker, "RANK_MAX", 4)
    cands = [cand(person_id=i) for i in range(1, 6)]
    replies = [{"ranked": [entry(1, 70, ["Operations Manager"]), entry(2, 60, ["Operations Manager"])]},
               {"ranked": [entry(3, 50, ["Operations Manager"]), entry(4, 45, ["Operations Manager"])]}]
    result, call_id = _rank_with(conn, replies, cands)
    assert [r["person_id"] for r in result["ranked"]] == [1, 2, 3, 4] and call_id.count(",") == 1
    assert result["excluded"] == [{"person_id": 5, "name": "A B", "score": None, "title": "Operations Manager",
                                   "why": "not scored: beyond the top 4 by search relevance"}]
