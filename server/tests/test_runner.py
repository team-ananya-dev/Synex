import json
import re
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import llm
from app.crustdata.people import months_before
from app.jobs import runner
from app.main import app

TODAY = date.today()


class FakeAnthropic:
    """Answers each stage's tool call from its schema; no network."""
    def __init__(self, screen_verdict="allow"):
        self.screen_verdict = screen_verdict
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        props = kw["tools"][0]["input_schema"]["properties"]
        user = kw["messages"][0]["content"]
        if "verdict" in props:
            reply = {"verdict": self.screen_verdict, "reason": "ok" if self.screen_verdict == "allow" else "asks for confidential data",
                     "rewritten_question": ""}
        elif "subquestions" in props:
            sub = {"text": "How does Acme run operations?", "expertise": "operations", "title_keywords": ["operations", "logistics"],
                   "target_companies": [{"name": "Acme", "basis": "named"}]}
            reply = {"subquestions": [sub, sub, sub]}
        elif "company_id" in props:
            reply = {"company_id": int(re.search(r"id (\d+)", user).group(1)), "reason": "fits", "confident": True}
        else:
            ids = [int(i) for i in re.findall(r"person_id (\d+)", user)]
            reply = {"ranked": [{"person_id": i, "score": 60 + i, "evidence": ["Operations Manager"], "reason": "ops role",
                                 "data_conflict": ""} for i in ids]}
        block = SimpleNamespace(type="tool_use", input=reply, id="t")
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def person(pid, company_id, current=False, rival=None):
    return {"crustdata_person_id": pid, "basic_profile": {"name": f"P{pid}", "headline": "h"}, "metadata": {},
            "social_handles": {"professional_network_identifier": {"profile_url": f"https://example.test/in/{pid}"}},
            "experience": {"employment_details": {
                "past": [{"crustdata_company_id": company_id, "title": "Operations Manager",
                          "start_date": months_before(TODAY, 30).isoformat() + "T00:00:00",
                          "end_date": months_before(TODAY, 10).isoformat() + "T00:00:00"}],
                "current": ([{"crustdata_company_id": company_id, "name": "Acme"}] if current else [])
                           + ([{"crustdata_company_id": 99, "name": "Rival", "company_website": "https://rival.com", "title": "Head of Ops",
                                "seniority_level": "Director"}] if rival else [])}}}


def crustdata(request):
    SEEN.append((request.url.path, json.loads(request.content) if request.content else None))
    if request.url.path == "/company/identify":
        match = lambda i, n: {"confidence_score": 1.0, "company_data": {"basic_info": {"crustdata_company_id": i, "name": n}}}
        return httpx.Response(200, json=[{"matches": [match(11, "Acme"), match(12, "Acme Other")]}], headers={"X-Credits-Used": "0.2"})
    if request.url.path == "/company/enrich":
        comp = {"organic_seo": ["rival.com", " other.com"], "paid_seo": [], "all_domains": ["noise.com"]}
        return httpx.Response(200, json=[{"matches": [{"company_data": {"competitors": comp}}]}], headers={"X-Credits-Used": "2.0"})
    if request.url.path == "/person/search":
        return httpx.Response(200, json={"profiles": [{**person(1, 11), "fit": "strong"}, person(2, 11, current=True), person(3, 11, rival=True)], "total_count": 2},
                              headers={"X-Credits-Used": "1.0"})
    if request.url.path == "/person/enrich":
        body = json.loads(request.content)
        url = body["professional_network_profile_urls"][0]
        data = person(1, 11)
        data["experience"]["employment_details"]["past"][0]["description"] = "Ran rider allocation for 40 stores"
        data["skills"] = {"professional_network_skills": ["Logistics"]}
        return httpx.Response(200, json=[{"matched_on": url, "matches": [{"person_data": data}]}], headers={"X-Credits-Used": "1.0"})
    return httpx.Response(404)


SEEN = []


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNEX_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("CRUSTDATA_API_KEY", "test")
    monkeypatch.setenv("SYNEX_ANTHROPIC_KEY", "test")
    monkeypatch.delenv("SYNEX_DEMO", raising=False)
    monkeypatch.setattr(runner, "crustdata_transport", httpx.MockTransport(crustdata))
    fake = {"v": FakeAnthropic()}
    monkeypatch.setattr(llm.anthropic, "Anthropic", lambda **k: fake["v"])
    return TestClient(app), fake


def events(client, case_id):
    with client.stream("GET", f"/cases/{case_id}/events") as r:
        text = "".join(r.iter_text())
    return [json.loads(b.split("data: ", 1)[1]) for b in text.split("\n\n") if "data: " in b]


def test_full_run_streams_stages_and_ends_paused(api):
    client, _ = api
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    evs = events(client, cid)
    done = [e["stage"] for e in evs if e["type"] == "stage.done"]
    assert done == ["s1_question_screen", "s2_decomposer", "s3_sourcer", "s4_people_screen", "s5_ranker", "s5b_enrich_rerank"]
    assert evs[-1]["type"] == "job.paused"
    states = [e["state"] for e in evs if e["type"] == "case.state"]
    assert states == ["PLANNED", "SOURCING"]

    view = client.get(f"/cases/{cid}").json()
    assert view["state"] == "SOURCING"
    ranked = view["stages"]["s5_ranker"]["1"]["ranked"]
    assert [r["person_id"] for r in ranked] == [1]  # person 2 still works at Acme and failed the screen
    assert ranked[0]["evidence"] == ["Operations Manager"] and ranked[0]["crustdata_fit"] == "strong"
    final = view["stages"]["s5b_enrich_rerank"]["1"]
    assert final["enriched_person_ids"] == [1]
    assert final["ranked"][0]["role_description"] == "Ran rider allocation for 40 stores"
    s4 = view["stages"]["s4_people_screen"]["1"]
    assert {s["person_id"]: s["verdict"] for s in s4} == {1: "pass", 2: "fail", 3: "fail"}
    assert any("direct competitor" in r["reason"] for r in next(s for s in s4 if s["person_id"] == 3)["results"])
    company = view["stages"]["s3_sourcer"]["1"]["companies"][0]
    assert company["competitor_domains"] == ["other.com", "rival.com"] and company["competitors_call_id"]
    assert view["cost"]["crustdata_credits"] > 0 and view["cost"]["model_usd"] > 0


def test_search_sends_relevance_query_and_hard_filters(api):
    client, _ = api
    SEEN.clear()
    client.post("/cases", json={"question": "What does Acme do?"})
    body = next(b for path, b in SEEN if path == "/person/search")
    assert body["mode"] == "exact" and body["search"]["query"].startswith("operations: ")
    fields = [c["field"] for c in body["filters"]["conditions"]]
    assert "experience.employment_details.current.company_id" in fields  # current employees excluded in the query
    assert body["limit"] == 5  # dev limit


def test_failed_competitor_lookup_gives_review_not_a_silent_pass(api, monkeypatch):
    client, _ = api

    def handler(request):
        return httpx.Response(500, text="down") if request.url.path == "/company/enrich" else crustdata(request)

    monkeypatch.setattr(runner, "crustdata_transport", httpx.MockTransport(handler))
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    view = client.get(f"/cases/{cid}").json()
    assert view["state"] == "SOURCING"
    s4 = {s["person_id"]: s["verdict"] for s in view["stages"]["s4_people_screen"]["1"]}
    assert s4[1] == "review" and s4[3] == "review"
    assert any(e["type"] == "competitor.lookup_failed" for e in events(client, cid))


def test_dev_limit_runs_two_subquestions_only(api):
    client, _ = api
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    assert sorted(client.get(f"/cases/{cid}").json()["stages"]["s3_sourcer"]) == ["1", "2"]


def test_refused_question_stops_early(api):
    client, fake = api
    fake["v"] = FakeAnthropic("refuse")
    cid = client.post("/cases", json={"question": "Tell me Acme's unreleased revenue"}).json()["id"]
    view = client.get(f"/cases/{cid}").json()
    assert view["state"] == "REFUSED" and view["refusal_reason"]
    assert "s2_decomposer" not in view["stages"]
    assert events(client, cid)[-1]["state"] == "REFUSED"


def test_stage_failure_marks_case_failed(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(runner, "crustdata_transport", httpx.MockTransport(lambda r: httpx.Response(500, text="down")))
    cid = client.post("/cases", json={"question": "What does Acme do?"}).json()["id"]
    assert client.get(f"/cases/{cid}").json()["state"] == "FAILED"
    evs = events(client, cid)
    assert any(e["type"] == "stage.failed" and e["stage"] == "s3_sourcer" for e in evs)


def test_unknown_case_is_404_and_short_question_rejected(api):
    client, _ = api
    assert client.get("/cases/nope").status_code == 404
    assert client.post("/cases", json={"question": "hi"}).status_code == 422
