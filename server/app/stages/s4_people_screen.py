"""Stage 4: fixed compliance rules in plain code. One function per rule; each returns
(passed, reason). Rules 4 (competitor conflict) and 7 (closed period) need company data
the sourcer does not fetch yet and are not implemented here."""
import re
from datetime import date

from ..crustdata.people import months_before

RESTRICTED_NAMES: set[str] = set()  # hard-coded restricted list (rule 5); empty until the team fills it

SENSITIVE = re.compile(
    r"\b(chief|ceo|cfo|coo|cto|ciso|chro|president|board|director of legal|general counsel|legal|counsel|"
    r"investor relations|controller|compliance|security)\b", re.I)


def rule_not_current(c: dict, today: date, p: dict):
    if c["still_at_company"]:
        return False, "profile still lists the target company as a current employer"
    return True, "no current role at the target company"


def rule_cooling_off(c, today, p):
    if not c["end_date"]:
        return False, "no exit date on record"
    if c["end_date"] > months_before(today, p["min_left"]).isoformat():
        return False, f"left {c['end_date']}, less than {p['min_left']} months ago"
    return True, f"left {c['end_date']}, at least {p['min_left']} months ago"


def rule_freshness(c, today, p):
    if not c["end_date"]:
        return False, "no exit date on record"
    if c["end_date"] < months_before(today, p["max_left"]).isoformat():
        return False, f"left {c['end_date']}, more than {p['max_left']} months ago"
    return True, f"left {c['end_date']}, within {p['max_left']} months"


def rule_min_tenure(c, today, p):
    t = c["tenure_months"]
    if t is None:
        return False, "no start date on record"
    if t < p["min_years"] * 12:
        return False, f"{t} months at the company, below {p['min_years'] * 12}"
    return True, f"{t} months at the company"


def rule_restricted(c, today, p):
    if c["name"].lower() in RESTRICTED_NAMES:
        return False, "on the restricted list"
    return True, "not on the restricted list"


FAIL_RULES = [rule_not_current, rule_cooling_off, rule_freshness, rule_min_tenure, rule_restricted]


def screen(candidate: dict, today: date, params: dict) -> dict:
    """verdict: pass | review (manual review flag, rule 6) | fail. Every rule's reason is kept."""
    results = []
    for rule in FAIL_RULES:
        ok, reason = rule(candidate, today, params)
        results.append({"rule": rule.__name__, "passed": ok, "reason": reason})
    verdict = "pass" if all(r["passed"] for r in results) else "fail"
    if verdict == "pass" and candidate["title"] and SENSITIVE.search(candidate["title"]):
        results.append({"rule": "rule_sensitive_role", "passed": True, "flag": True,
                        "reason": f"title {candidate['title']!r} is a sensitive role: manual review"})
        verdict = "review"
    return {"person_id": candidate["person_id"], "verdict": verdict, "results": results}
