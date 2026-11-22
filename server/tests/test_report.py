"""Client report (Ananya): the PDF, its overview, and that it never carries personal data."""
import io
import re
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from app.core import db
from app.report import overview
from tests.test_expert import sent  # noqa: F401  (fixture)
from tests.test_outreach import smtp  # noqa: F401  (fixture)
from tests.test_response_screen import ScreenFake, submit
from tests.test_runner import api, db_events  # noqa: F401  (fixtures and helpers)


class ReportFake:
    """Screens answers, writes summaries and the overview with scripted replies; other stages go to Dev's fake."""
    def __init__(self, base, overview_reply=None):
        self.base, self.overview_reply, self.calls = ScreenFake(base, {"verdict": "accepted", "reason": "fine", "flagged_spans": []}), overview_reply, {"summary": 0, "overview": 0}
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        props = kw["tools"][0]["input_schema"]["properties"]
        user = kw["messages"][0]["content"]
        refs = re.findall(r"\[(E[0-9a-f]{8})\]", user)
        if "headline" in props:
            self.calls["overview"] += 1
            if self.overview_reply == "bad":
                reply = {"headline": {"text": "wrong shape", "cites": []}, "headline_cites": [], "key_findings": [], "next_questions": []}
            else:
                reply = {"headline": "Teams grew steadily over two years.", "headline_cites": refs[:1],
                         "key_findings": [{"text": "A supported point about steady growth.", "cites": refs[:1]},
                                          {"text": "An unsupported point with no source.", "cites": []},
                                          {"text": "A point citing someone not in the case.", "cites": ["Edeadbeef0"[:9]]}],
                         "next_questions": ["Q one?", "Q two?", "Q three?", "Q four?"]}
        elif "agreement" in props.get("subquestions", {}).get("items", {}).get("properties", {}):
            self.calls["summary"] += 1
            idx = [int(i) for i in re.findall(r"Sub-question (\d+):", user)]
            reply = {"subquestions": [{"index": i, "agreement": "n/a", "sentences": [f"Teams grew over time. [{refs[0]}]"]} for i in idx]}
        else:
            return self.base.messages.create(**kw)
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=reply, id="t")], usage=SimpleNamespace(input_tokens=200, output_tokens=40))


def setup(api, sent, overview_reply=None):
    client, cid, token, indices = sent
    _, fake = api
    fake["v"] = ReportFake(fake["v"], overview_reply)
    submit(client, token, indices, ["Teams grew steadily over two years, roughly doubling in size."] * len(indices))
    return client, cid, fake["v"]


def text(pdf_bytes: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf_bytes)).pages)


def test_report_needs_an_accepted_answer_and_a_real_case(api, sent):
    client, cid, _, _ = sent
    assert client.get(f"/customer/cases/{cid}/report.pdf").status_code == 409
    assert client.post(f"/customer/cases/{cid}/report/prepare").status_code == 409
    assert client.get("/customer/cases/nope/report.pdf").status_code == 404


def test_pdf_has_the_expected_sections_and_no_personal_data(api, sent):
    client, cid, _ = setup(api, sent)
    r = client.get(f"/customer/cases/{cid}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content[:5] == b"%PDF-"
    assert f"synex-report-{cid}.pdf" in r.headers["content-disposition"]
    pages = PdfReader(io.BytesIO(r.content)).pages
    assert len(pages) >= 4
    body = text(r.content)
    for expected in ("Executive summary", "Findings by sub-question", "Evidence at a glance", "Appendix D. Audit trail and cost",
                     "Audit chain verified", "roughly doubling in size", cid, "Page 2 of"):
        assert expected in body, expected
    # no name, address or link of the real person behind the persona (Dev's fixture person is "Quentin Zephyr...")
    assert "Quentin" not in body and "Zephyr" not in body and "@" not in body and "http" not in body.lower() and "linkedin" not in body.lower()
    gen = [e for e in db_events(cid) if e["type"] == "report.generated"]
    assert gen and gen[0]["bytes"] == len(r.content) and gen[0]["with_overview"] is False


def test_overview_is_cite_or_drop_stored_once_and_shown_in_the_pdf(api, sent):
    client, cid, fake = setup(api, sent)
    p = client.post(f"/customer/cases/{cid}/report/prepare").json()
    assert p["summary"] == "written" and p["overview"] == "written" and p["ready"] is True
    assert fake.calls == {"summary": 1, "overview": 1}
    again = client.post(f"/customer/cases/{cid}/report/prepare").json()
    assert again["overview"] == "written" and fake.calls == {"summary": 1, "overview": 1}     # same answers: no new model call
    conn = db.connect()
    stored = overview.stored(conn, cid, __import__("app.stages.s8_result", fromlist=["x"]).compute(conn, cid))
    assert stored["headline"]["text"].startswith("Teams grew") and len(stored["key_findings"]) == 1
    assert stored["dropped_uncited"] == 2 and len(stored["next_questions"]) == 3                 # two bad findings dropped, questions capped
    body = text(client.get(f"/customer/cases/{cid}/report.pdf").content)
    assert "Teams grew steadily over two years." in body and "A supported point about steady growth." in body
    assert "An unsupported point" not in body and "someone not in the case" not in body
    assert "Q one?" in body and "Q four?" not in body
    assert "report.overview_written" in [e["type"] for e in db_events(cid)]


def test_a_model_failure_still_gives_a_report_without_the_overview(api, sent):
    client, cid, fake = setup(api, sent, overview_reply="bad")
    p = client.post(f"/customer/cases/{cid}/report/prepare")
    assert p.status_code == 200 and p.json()["overview"] == "unavailable" and p.json()["overview_error"]
    r = client.get(f"/customer/cases/{cid}/report.pdf")
    assert r.status_code == 200
    assert "A written overview was not available" in text(r.content)


def test_new_answers_make_the_stored_overview_stale(api, sent):
    client, cid, _ = setup(api, sent)
    client.post(f"/customer/cases/{cid}/report/prepare")
    conn = db.connect()
    from app.stages import s8_result
    res = s8_result.compute(conn, cid)
    assert overview.stored(conn, cid, res) is not None
    res["subquestions"][0]["answers"].append({"response_id": "Rnew00000", "ref": "E00000000"})   # a new accepted answer arrives
    assert overview.stored(conn, cid, res) is None


def test_overview_check_unit():
    reply = {"headline": "H", "headline_cites": ["E11111111"],
             "key_findings": [{"text": "ok", "cites": ["E11111111"]}, {"text": "none", "cites": []}, {"text": "", "cites": ["E11111111"]},
                              {"text": "foreign", "cites": ["E22222222"]}],
             "next_questions": ["a?", " ", "b?", "c?", "d?"]}
    out, dropped = overview.check(reply, {"E11111111"})
    assert out["headline"]["cites"] == ["E11111111"] and [f["text"] for f in out["key_findings"]] == ["ok"] and dropped == 3
    assert out["next_questions"] == ["a?", "b?", "c?"]
    out, dropped = overview.check({**reply, "headline_cites": []}, {"E11111111"})
    assert out["headline"] is None and dropped == 4
    with pytest.raises(ValueError):
        overview.validate({"headline": {"text": "x"}, "headline_cites": [], "key_findings": []})
