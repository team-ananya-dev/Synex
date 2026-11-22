"""The three submitted test cases (tests/cases/*.json): real Crustdata records, the request, and the correct result.
Each is run through the same sourcer normalisation and people screen the service uses."""
import json
from datetime import date
from pathlib import Path

import pytest

from app.stages import s3_sourcer, s4_people_screen

CASES = sorted((Path(__file__).resolve().parents[2] / "tests" / "cases").glob("*.json"))


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_case_gives_the_correct_result(path):
    case = json.loads(path.read_text())
    req, src, expected = case["request"], case["sources"], case["expected"]
    profile = {**case["record_excerpt"], "basic_profile": {"name": "Expert"}}   # names are not stored in the case
    today = date.fromisoformat(req["as_of"])
    cand = s3_sourcer.normalise(profile, req["target_company"]["crustdata_company_id"], src["person_record"]["call_id"], today)
    rules = req["rules"]
    result = s4_people_screen.screen(cand, today, {"min_left": rules["min_left_months"], "max_left": rules["max_left_months"],
                                                    "min_years": rules["min_years"],
                                                    "competitor_domains": src["competitor_list"]["domains"]})
    assert result["verdict"] == expected["verdict"]
    assert [r["rule"] for r in result["results"] if r["passed"] is False] == expected["failed_rules"]
    assert [r["rule"] for r in result["results"] if r["passed"] is None] == expected["cannot_verify_rules"]
    for r in result["results"]:          # every fact cites its field, the record date and the call
        if r["rule"].startswith("rule_") and not r.get("flag"):
            assert r["field_path"] and r["record_date"] == src["person_record"]["record_updated_at"]
            assert r["source_call_id"] == src["person_record"]["call_id"]


def test_there_are_three_cases_covering_pass_fail_and_cannot_verify():
    verdicts = sorted(json.loads(p.read_text())["expected"]["verdict"] for p in CASES)
    assert verdicts == ["cannot_verify", "fail", "pass"]
