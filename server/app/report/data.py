"""Everything the client report states, gathered from the database. Customer-safe only: no name, headline, profile
link, city or email ever enters this dictionary. Counts of people are aggregates; experts appear by their anonymous
ref, a coarse role label, their company, a tenure band, the year they left and their country.

Every figure here is computed from records the screens already show (stage results, screened responses, the audit
chain, the cost log). Nothing is typed in and nothing is invented.
"""
import json
import re
from datetime import datetime, timezone

from ..core.events import verify_chain
from ..jobs import views
from ..stages import s8_result

PROVENANCE = (
    "This report comes from a demonstration build of Synex. The experts' answers were given by members of the Synex "
    "team answering in the role of the former employees the system found; every invitation went to a team member's "
    "inbox, and no real person was contacted. The people, roles and companies were found in live Crustdata data. "
    "Treat the answers as a demonstration of the method, not as evidence about the companies."
)

RULE_LABELS = [
    ("not_current", "Still employed at the company"),
    ("cooling_off", "Left too recently (cooling-off period)"),
    ("freshness", "Left too long ago"),
    ("min_tenure", "Too short a time at the company"),
    ("competitor", "Conflict with a competitor"),
    ("restricted", "On the restricted list"),
]


def tenure_band(months: int | None) -> str:
    if months is None:
        return "not stated"
    return "under 1 year" if months < 12 else "1 to 3 years" if months < 36 else "3 to 5 years" if months < 60 else "5 years or more"


def _stage(conn, case_id: str, stage: str):
    r = conn.execute("SELECT result FROM stage_results WHERE case_id=? AND stage=? ORDER BY id DESC LIMIT 1", (case_id, stage)).fetchone()
    return json.loads(r["result"]) if r else None


def _rule_label(rule: str) -> str:
    for key, label in RULE_LABELS:
        if key in rule:
            return label
    return rule.replace("rule_", "").replace("_", " ").capitalize()


def _screening_breakdown(conn, case_id: str) -> dict:
    """People found, per sub-question outcome counts, and how many were removed by which rule. Aggregates only."""
    s3, s4 = _stage(conn, case_id, "s3_sourcer") or {}, _stage(conn, case_id, "s4_people_screen") or {}
    per_sub, by_rule, unique = [], {}, {}
    for idx, screens in s4.items():
        counts = {"considered": len(screens), "pass": 0, "review": 0, "fail": 0, "cannot_verify": 0}
        for s in screens:
            counts[s["verdict"]] = counts.get(s["verdict"], 0) + 1
            unique[s["person_id"]] = s["verdict"] if unique.get(s["person_id"]) in (None, "fail", "cannot_verify") else unique[s["person_id"]]
            if s["verdict"] in ("fail", "cannot_verify"):
                failed = [r for r in s["results"] if not r["passed"]] or [{"rule": "cannot_verify"}]
                for r in failed:
                    label = "Could not be verified (missing or ambiguous record)" if s["verdict"] == "cannot_verify" else _rule_label(r["rule"])
                    by_rule[label] = by_rule.get(label, 0) + 1
        per_sub.append({"index": int(idx), **counts})
    companies = {}
    for idx, v in s3.items():
        for c in v.get("companies", []):
            entry = companies.setdefault(c["asked"].strip().lower(), {
                "asked": c["asked"], "basis": c["basis"], "resolved": bool(c.get("resolved")),
                "name": (c.get("chosen") or {}).get("name"), "matches": c.get("total_matches"),
                "note": c.get("reason") if c.get("cannot_verify") else None})
    return {"per_subquestion": sorted(per_sub, key=lambda x: x["index"]),
            "removed_by_rule": dict(sorted(by_rule.items(), key=lambda kv: -kv[1])),
            "people_found": len(unique), "companies": sorted(companies.values(), key=lambda c: (c["basis"] != "named", c["asked"]))}


def _audit(conn, case_id: str) -> dict:
    row = conn.execute("SELECT COUNT(*) n, MIN(id) first_id, MAX(id) last_id FROM events WHERE case_id=?", (case_id,)).fetchone()
    first = conn.execute("SELECT hash, created_at FROM events WHERE case_id=? ORDER BY id LIMIT 1", (case_id,)).fetchone()
    last = conn.execute("SELECT hash, created_at FROM events WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    total = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
    ok, bad = verify_chain(conn)
    delivered = conn.execute("SELECT created_at FROM events WHERE case_id=? AND type='case.state' AND payload LIKE '%DELIVERED%' ORDER BY id LIMIT 1", (case_id,)).fetchone()
    return {"events": row["n"], "first_hash": first["hash"] if first else None, "last_hash": last["hash"] if last else None,
            "started_at": first["created_at"] if first else None, "last_event_at": last["created_at"] if last else None,
            "delivered_at": delivered["created_at"] if delivered else None,
            "chain_ok": ok, "chain_first_bad": bad, "chain_events_checked": total}


def _calls(conn, case_id: str) -> dict:
    llm = [dict(r) for r in conn.execute(
        "SELECT purpose, COUNT(*) calls, COALESCE(SUM(input_tokens),0) tin, COALESCE(SUM(output_tokens),0) tout, "
        "COALESCE(SUM(cost_usd),0) usd FROM llm_calls WHERE case_id=? GROUP BY purpose ORDER BY MIN(id)", (case_id,))]
    cd = [dict(r) for r in conn.execute(
        "SELECT purpose, COUNT(*) calls, COALESCE(SUM(credits),0) credits FROM crustdata_calls WHERE case_id=? GROUP BY purpose ORDER BY MIN(id)", (case_id,))]
    return {"model": llm, "crustdata": cd}


def _questions_assigned(conn, case_id: str) -> dict | None:
    r = conn.execute("SELECT payload FROM events WHERE case_id=? AND type='questions.assigned' ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    return json.loads(r["payload"]) if r else None


def collect(conn, case_id: str) -> dict:
    """The full, customer-safe data of one case. Raises KeyError for an unknown case."""
    view = views.customer_view(conn, case_id)                      # 404 HTTPException for an unknown case is mapped by the caller
    result = s8_result.compute(conn, case_id)
    s1 = _stage(conn, case_id, "s1_question_screen") or {}
    cards = {c["ref"]: c for cs in view["panel"].values() for c in cs}
    answered_refs = {}
    for sq in result["subquestions"]:
        for a in sq["answers"]:
            card = cards.get(a["ref"], {})
            answered_refs.setdefault(a["ref"], {
                "ref": a["ref"], "role": a["role"], "company": a["company"], "tenure": tenure_band(card.get("tenure_months")),
                "left": card.get("left_year"), "country": card.get("country"), "mode": a["mode"], "answers": 0})
            answered_refs[a["ref"]]["answers"] += 1
    experts_responded = conn.execute("SELECT COUNT(DISTINCT person_id) n FROM responses WHERE case_id=?", (case_id,)).fetchone()["n"]
    coverage_total = {k: sum(sq["coverage"][k] for sq in result["subquestions"]) for k in ("received", "pending", "accepted", "redacted", "held", "rejected")}
    plan = {p["index"]: p for p in (view["plan"] or [])}
    for sq in result["subquestions"]:
        sq["expertise"] = (plan.get(sq["index"]) or {}).get("expertise")
        sq["target_companies"] = [c["name"] for c in (plan.get(sq["index"]) or {}).get("target_companies", [])]
    tally = {"High": 0, "Medium": 0, "Low": 0}
    for sq in result["subquestions"]:
        if sq["confidence"]:
            tally[sq["confidence"]] += 1
    audit = _audit(conn, case_id)
    case = conn.execute("SELECT params FROM cases WHERE id=?", (case_id,)).fetchone()
    params = json.loads(case["params"]) if case else {}
    return {
        "case_id": case_id, "question": view["question"], "state": view["state"], "created_at": view["created_at"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "screen": {"verdict": s1.get("verdict"), "reason": s1.get("reason"), "effective_question": s1.get("effective_question"),
                   "named_companies": s1.get("named_companies") or []},
        "plan": view["plan"] or [], "result": result, "tally": tally, "coverage_total": coverage_total,
        "experts": sorted(answered_refs.values(), key=lambda e: e["ref"]),
        "outreach": {"invited": sum(view["outreach"].values()), "by_status": view["outreach"], "experts_responded": experts_responded,
                     "panel_size": (view.get("approval") or {}).get("panel_size"), "questions": _questions_assigned(conn, case_id)},
        "sourcing": _screening_breakdown(conn, case_id),
        "window": {"min_left": params.get("min_left", 6), "max_left": params.get("max_left", 24), "min_years": params.get("min_years", 1)},
        "audit": audit, "calls": _calls(conn, case_id), "cost": view["cost"], "provenance": PROVENANCE,
    }


def safe_text(s: str | None) -> str:
    """Plain text for PDF paragraphs: escape markup characters and collapse whitespace."""
    s = re.sub(r"\s+", " ", s or "").strip()
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
