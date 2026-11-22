"""Stage 8 result (Dev): independence rule, labels, confidence, and the cited summary checker."""
from types import SimpleNamespace

from app.core import db
from app.stages import s8_result as s8
from tests.test_expert import sent  # noqa: F401  (fixture)
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_response_screen import script, submit
from tests.test_runner import api, db_events  # noqa: F401  (fixtures and helpers)


def hist(company=1, function="Operations", city="Pune, Maharashtra, India", start="2020-01-01", end="2022-01-01"):
    return {"company_id": company, "function": function, "location": city, "start_date": start, "end_date": end}


def ans(pid, ref):
    return {"person_id": pid, "ref": ref, "company": "Acme"}


# ---- independence rule ------------------------------------------------------------------------

def test_same_company_function_city_and_overlap_is_one_source():
    history = {1: hist(), 2: hist(start="2021-01-01", end="2023-06-01"), 3: hist(company=2)}
    groups, unchecked = s8.group_sources([ans(1, "Ea"), ans(2, "Eb"), ans(3, "Ec")], history)
    assert sorted(len(g["refs"]) for g in groups) == [1, 2] and unchecked == []
    merged = next(g for g in groups if len(g["refs"]) == 2)
    assert "overlapped 12 months" in merged["evidence"] and "Pune" not in merged["evidence"]   # no city named


def test_short_overlap_or_other_function_or_city_stays_independent():
    base = hist()
    assert s8.same_source(base, hist(start="2021-11-01", end="2023-01-01")) == (False, 2)
    assert s8.same_source(base, hist(function="Finance"))[0] is False
    assert s8.same_source(base, hist(city="Delhi, India"))[0] is False
    assert s8.same_source(base, hist(start="2022-03-01", end="2024-01-01")) == (False, 0)   # no overlap


def test_missing_work_history_counts_separately_and_is_flagged():
    history = {1: hist(), 2: {**hist(), "location": None}}
    groups, unchecked = s8.group_sources([ans(1, "Ea"), ans(2, "Eb"), ans(9, "Ez")], history)
    assert len(groups) == 3
    assert {u["ref"]: u["missing"] for u in unchecked} == {"Eb": ["location"], "Ez": ["work history"]}


def test_merging_is_transitive():
    history = {1: hist(start="2019-01-01", end="2020-06-01"), 2: hist(start="2020-01-01", end="2021-06-01"),
               3: hist(start="2021-01-01", end="2022-06-01")}       # 1~2 and 2~3, 1 and 3 never overlapped
    groups, _ = s8.group_sources([ans(1, "Ea"), ans(2, "Eb"), ans(3, "Ec")], history)
    assert len(groups) == 1


def test_confidence_thresholds():
    assert [s8.confidence(n) for n in (0, 1, 2, 3, 5)] == [None, "Low", "Medium", "High", "High"]


def test_checker_drops_uncited_and_foreign_citations():
    kept, dropped = s8.check_sentences(
        ["Teams grew [E1a2b3c4d].", "No citation here.", "Cites someone else [Effffffff].", "Both [E1a2b3c4d][E00000000]."],
        {"E1a2b3c4d", "E00000000"})
    assert [k["text"] for k in kept] == ["Teams grew [E1a2b3c4d]."] and dropped == 3   # 4th sentence is over the limit of 3


# ---- through the API --------------------------------------------------------------------------

class SummaryFake:
    def __init__(self, base, sentences):
        self.base, self.sentences, self.calls = base, sentences, 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        sq = kw["tools"][0]["input_schema"]["properties"].get("subquestions", {})
        if "agreement" not in sq.get("items", {}).get("properties", {}):
            return self.base.messages.create(**kw)
        self.calls += 1
        import re
        indices = [int(i) for i in re.findall(r"Sub-question (\d+):", kw["messages"][0]["content"])]
        refs = re.findall(r"\[(E[0-9a-f]{8})\]", kw["messages"][0]["content"])
        reply = {"subquestions": [{"index": i, "agreement": "n/a",
                                   "sentences": [s.replace("{ref}", refs[0]) for s in self.sentences]} for i in indices]}
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=reply, id="t")],
                               usage=SimpleNamespace(input_tokens=300, output_tokens=60))


def test_result_counts_only_accepted_answers_and_hides_identity(api, sent):
    client, cid, token, indices = sent
    assert client.get("/customer/cases/nope/result").status_code == 404
    before = client.get(f"/customer/cases/{cid}/result").json()
    assert all(sq["status"] == "no accepted answer" and sq["confidence"] is None for sq in before["subquestions"])
    assert client.post(f"/customer/cases/{cid}/result/summary").status_code == 409

    script(api, {"verdict": "accepted", "reason": "general experience", "flagged_spans": []},
           {"verdict": "held", "reason": "unsure", "flagged_spans": []})
    submit(client, token, indices, [f"Rider pools were shared across stores ({i})" for i in indices])
    res = client.get(f"/customer/cases/{cid}/result").json()
    first = next(sq for sq in res["subquestions"] if sq["index"] == indices[0])
    assert first["status"] == "answered" and first["independent_sources"] == 1
    assert first["label"] == "single source" and first["confidence"] == "Low" and first["label_basis"] == "code"
    assert first["answers"][0]["ref"].startswith("E") and "person_id" not in first["answers"][0]
    if len(indices) > 1:
        held = next(sq for sq in res["subquestions"] if sq["index"] == indices[1])
        assert held["status"] == "no accepted answer" and held["coverage"]["held"] == 1
    assert "Quentin" not in str(res) and "Pune" not in str(res)
    assert res["summary_status"] == "not written"


def test_summary_is_cited_checked_and_written_once(api, sent):
    client, cid, token, indices = sent
    script(api, {"verdict": "accepted", "reason": "general experience", "flagged_spans": []})
    submit(client, token, indices, [f"Rider pools were shared across stores ({i})" for i in indices])
    _, fake = api
    fake["v"] = summary = SummaryFake(fake["v"], ["Stores shared rider pools [{ref}].", "An uncited guess."])
    r = client.post(f"/customer/cases/{cid}/result/summary")
    assert r.status_code == 200, r.text
    sq = r.json()["subquestions"][0]
    assert [s["text"].split(" [")[0] for s in sq["summary"]["sentences"]] == ["Stores shared rider pools"]
    assert sq["summary"]["dropped_uncited"] == 1 and sq["label"] == "single source"
    assert client.post(f"/customer/cases/{cid}/result/summary").status_code == 200
    assert summary.calls == 1                                                    # same answers: no second call
    assert client.get(f"/customer/cases/{cid}/result").json()["summary_status"] == "written"
    assert [e["type"] for e in db_events(cid)].count("result.summary_written") == 1
    rows = db.connect().execute("SELECT COUNT(*) n FROM llm_calls WHERE purpose='result_summary'").fetchone()["n"]
    assert rows == 1


def test_model_label_applies_only_to_two_or_more_sources_and_stale_summary_is_hidden():
    def result(n):
        return {"summary_status": "not written", "subquestions": [
            {"index": 0, "independent_sources": n, "label": "x", "label_basis": "code", "summary": None}]}
    summary = {"fingerprint": "f1", "llm_call_id": "c1",
               "subquestions": {"0": {"agreement": "split", "sentences": [], "dropped_uncited": 0}}}
    two = s8._attach(result(2), summary, "f1")["subquestions"][0]
    assert (two["label"], two["label_basis"]) == ("split", "model")
    assert s8._attach(result(1), summary, "f1")["subquestions"][0]["label"] == "x"
    stale = s8._attach(result(2), summary, "f2")
    assert stale["summary_status"] == "stale" and stale["subquestions"][0]["summary"] is None
