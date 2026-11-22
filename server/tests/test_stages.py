from datetime import date
from types import SimpleNamespace

import pytest

from app.core import db, llm
from app.stages import s3_sourcer, s4_people_screen, s5_ranker

TODAY = date(2026, 11, 22)
PARAMS = {"min_left": 6, "max_left": 24, "min_years": 1}


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


def test_ranker_retries_once_on_invalid_reply_and_logs_both():
    conn = db.connect(":memory:")
    fake = FakeAnthropic([{"ranked": [{"person_id": 99, "score": 5, "reason": "x"}]},
                          {"ranked": [{"person_id": 1, "score": 70, "reason": "fits"}]}])
    orig = llm.anthropic.Anthropic
    llm.anthropic.Anthropic = lambda **k: fake
    try:
        import os
        os.environ["SYNEX_ANTHROPIC_KEY"] = "test"
        ranked, _ = s5_ranker.rank(conn, [cand()], "q", "ops", "c1")
    finally:
        llm.anthropic.Anthropic = orig
    assert ranked[0]["score"] == 70
    rows = conn.execute("SELECT attempt, valid FROM llm_calls ORDER BY id").fetchall()
    assert [(r["attempt"], r["valid"]) for r in rows] == [(1, 0), (2, 1)]
    assert llm.spent_usd(conn) > 0


def test_budget_blocks_calls(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setattr(llm, "BUDGET_USD", 0.0)
    with pytest.raises(llm.BudgetExceeded):
        llm.call_json(conn, purpose="t", system="s", user="u", schema={"type": "object"}, client=FakeAnthropic([{}]))
