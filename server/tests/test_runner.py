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
            reply = {"ranked": [{"person_id": i, "score": 60 + i, "reason": "ops role"} for i in ids]}
        block = SimpleNamespace(type="tool_use", input=reply, id="t")
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def person(pid, company_id, current=False):
    return {"crustdata_person_id": pid, "basic_profile": {"name": f"P{pid}", "headline": "h"}, "metadata": {},
            "experience": {"employment_details": {
                "past": [{"crustdata_company_id": company_id, "title": "Operations Manager",
                          "start_date": months_before(TODAY, 30).isoformat() + "T00:00:00",
                          "end_date": months_before(TODAY, 10).isoformat() + "T00:00:00"}],
                "current": [{"crustdata_company_id": company_id, "name": "Acme"}] if current else []}}}


def crustdata(request):
    if request.url.path == "/company/identify":
        match = lambda i, n: {"confidence_score": 1.0, "company_data": {"basic_info": {"crustdata_company_id": i, "name": n}}}
        return httpx.Response(200, json=[{"matches": [match(11, "Acme"), match(12, "Acme Other")]}], headers={"X-Credits-Used": "0.2"})
    if request.url.path == "/person/search":
        return httpx.Response(200, json={"profiles": [person(1, 11), person(2, 11, current=True)], "total_count": 2},
                              headers={"X-Credits-Used": "1.0"})
    return httpx.Response(404)


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
    assert done == ["s1_question_screen", "s2_decomposer", "s3_sourcer", "s4_people_screen", "s5_ranker"]
    assert evs[-1]["type"] == "job.paused"
    states = [e["state"] for e in evs if e["type"] == "case.state"]
    assert states == ["PLANNED", "SOURCING"]

    view = client.get(f"/cases/{cid}").json()
    assert view["state"] == "SOURCING"
    ranked = view["stages"]["s5_ranker"]["1"]["ranked"]
    assert [r["person_id"] for r in ranked] == [1]  # person 2 still works at Acme and failed the screen
    s4 = view["stages"]["s4_people_screen"]["1"]
    assert {s["person_id"]: s["verdict"] for s in s4} == {1: "pass", 2: "fail"}
    assert view["cost"]["crustdata_credits"] > 0 and view["cost"]["model_usd"] > 0


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
