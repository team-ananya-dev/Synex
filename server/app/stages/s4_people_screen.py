"""Stage 4: fixed compliance rules in plain code. One function per rule; each returns
(passed, reason). Rule 7 (closed period) needs listing and earnings data the sourcer does not fetch yet and is
not implemented here."""
import re
from datetime import date

from ..crustdata.people import months_before

PARTNER_NAMES: set[str] = set()  # listed partners (rule 4), lower case; empty until the team fills it
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


SENIOR_LEVELS = {"experienced manager", "director", "vice president", "cxo", "owner / partner"}
STRATEGIC = re.compile(r"\b(head|strategy|strategic|pricing|product|category|procurement|sourcing|business development|"
                       r"growth|finance|analytics|chief)\b", re.I)


def _host(url: str | None) -> str:
    u = (url or "").strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    u = u.split("/")[0]
    return u[4:] if u.startswith("www.") else u


def _squash(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def competitor_roles(c: dict, competitor_hosts: list[str]) -> list[dict]:
    """Current roles at a direct competitor or listed partner. A role matches when the employer's website
    is a competitor domain, or its name equals a competitor's domain name (Quickmart vs quickmart.in)."""
    labels = {h.split(".")[0] for h in competitor_hosts}
    out = []
    for r in c.get("current_roles", []):
        name = _squash(r["name"])
        if _host(r["website"]) in competitor_hosts or (name and name in labels) or (r["name"] or "").lower() in PARTNER_NAMES:
            out.append(r)
    return out


def is_sensitive_role(r: dict) -> bool:
    return (r["seniority"] or "").lower() in SENIOR_LEVELS or bool(r["title"] and (STRATEGIC.search(r["title"]) or SENSITIVE.search(r["title"])))


def rule_competitor(c, today, p):
    """Rule 4. Fails on a sensitive current role at a direct competitor. Any other role at a competitor,
    or a competitor list that could not be fetched, is a manual review flag (see screen)."""
    hosts = p.get("competitor_domains")
    if hosts is None:
        return True, "competitor list unavailable, not checked"
    bad = [r for r in competitor_roles(c, hosts) if is_sensitive_role(r)]
    if bad:
        return False, f"now {bad[0]['title']!r} ({bad[0]['seniority'] or 'level unknown'}) at {bad[0]['name']}, a direct competitor"
    return True, "no sensitive current role at a direct competitor"


def rule_restricted(c, today, p):
    if c["name"].lower() in RESTRICTED_NAMES:
        return False, "on the restricted list"
    return True, "not on the restricted list"


FAIL_RULES = [rule_not_current, rule_cooling_off, rule_freshness, rule_min_tenure, rule_competitor, rule_restricted]


def screen(candidate: dict, today: date, params: dict) -> dict:
    """verdict: pass | review (manual review flag, rule 6) | fail. Every rule's reason is kept."""
    results = []
    for rule in FAIL_RULES:
        ok, reason = rule(candidate, today, params)
        results.append({"rule": rule.__name__, "passed": ok, "reason": reason})
    verdict = "pass" if all(r["passed"] for r in results) else "fail"
    if verdict == "pass":  # rule 4 flags: a lesser role at a competitor, or no competitor list to check against
        hosts = params.get("competitor_domains")
        if hosts is None:
            results.append({"rule": "rule_competitor", "passed": True, "flag": True,
                            "reason": "competitor list could not be fetched: manual review"})
            verdict = "review"
        elif competitor_roles(candidate, hosts):
            r = competitor_roles(candidate, hosts)[0]
            results.append({"rule": "rule_competitor", "passed": True, "flag": True,
                            "reason": f"now {r['title']!r} at {r['name']}, a direct competitor, in a non-sensitive role: manual review"})
            verdict = "review"
    if verdict == "pass" and candidate["title"] and SENSITIVE.search(candidate["title"]):
        results.append({"rule": "rule_sensitive_role", "passed": True, "flag": True,
                        "reason": f"title {candidate['title']!r} is a sensitive role: manual review"})
        verdict = "review"
    return {"person_id": candidate["person_id"], "verdict": verdict, "results": results}
