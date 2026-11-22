"""Two views of a case. The operator view has real people's names and profile links. The customer view
never does: a customer who sees them could contact the expert directly and skip the service."""
import hashlib
import json
import sqlite3

from fastapi import HTTPException

from ..actions import pricing, queue
from ..core import config


def _stages(conn, case_id: str) -> dict:
    out = {}
    for r in conn.execute("SELECT stage, result FROM stage_results WHERE case_id=? ORDER BY id", (case_id,)):
        out[r["stage"]] = json.loads(r["result"])
    return out


def _case(conn, case_id: str) -> sqlite3.Row:
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        raise HTTPException(404, "no such case")
    return case


def costs(conn, case_id: str) -> dict:
    credits = conn.execute("SELECT COALESCE(SUM(credits),0) c FROM crustdata_calls WHERE case_id=?", (case_id,)).fetchone()["c"]
    usd = conn.execute("SELECT COALESCE(SUM(cost_usd),0) c FROM llm_calls WHERE case_id=?", (case_id,)).fetchone()["c"]
    return {"crustdata_credits": credits, "model_usd": round(usd, 6), "credit_cap": config.case_credit_cap()}


def operator_view(conn, case_id: str) -> dict:
    case = _case(conn, case_id)
    return {"id": case["id"], "question": case["question"], "state": case["state"], "refusal_reason": case["refusal_reason"],
            "created_at": case["created_at"], "stages": _stages(conn, case_id), "cost": costs(conn, case_id)}


# ---- customer view -------------------------------------------------------------------------------

def expert_ref(case_id: str, person_id: int) -> str:
    """An opaque id for one expert inside one case. It cannot be reversed to the person."""
    return "E" + hashlib.sha256(f"{case_id}:{person_id}".encode()).hexdigest()[:8]


def _company_names(stages: dict) -> dict:
    return {str(c["chosen"]["company_id"]): c["chosen"]["name"]
            for v in stages.get("s3_sourcer", {}).values() for c in v["companies"] if c["resolved"]}


def card(case_id: str, p: dict, company_names: dict) -> dict:
    """An anonymised expert card: what they did and why they fit, with no name, headline, link or city."""
    quotable = " | ".join(str(x).lower() for x in [p.get("title"), p.get("function"), p.get("role_description"),
                                                   ", ".join(p.get("skills") or [])] if x)
    return {
        "ref": expert_ref(case_id, p["person_id"]), "role": p["title"], "company": company_names.get(str(p["company_id"])),
        "tenure_months": p["tenure_months"], "left_year": (p.get("end_date") or "")[:4] or None,
        "country": p.get("country"),
        "fit": p["fit"], "score": p["score"], "reason": p["reason"],
        # snippets from the headline are left out: a headline is easy to search for
        "evidence": [e for e in p["evidence"] if e.lower() in quotable],
    } | {"evidence_hidden": sum(1 for e in p["evidence"] if e.lower() not in quotable)}


def redact_stage_result(case_id: str, stage: str, result, stages: dict):
    names = _company_names(stages)
    if stage in ("s1_question_screen", "s2_decomposer"):
        return result
    if stage == "s3_sourcer":
        return {idx: {"companies": [{"asked": c["asked"], "basis": c["basis"], "resolved": c["resolved"],
                                     "name": c.get("chosen", {}).get("name"), "domain": c.get("chosen", {}).get("domain"),
                                     "total_matches": c.get("total_matches")} for c in v["companies"]],
                      "found": len(v["candidates"])} for idx, v in result.items()}
    if stage == "s4_people_screen":
        return {idx: {k: sum(1 for s in screens if s["verdict"] == k) for k in ("pass", "review", "fail")}
                for idx, screens in result.items()}
    if stage in ("s5_ranker", "s5b_enrich_rerank"):
        return {idx: {"panel": [card(case_id, p, names) for p in v["ranked"]], "left_off": len(v["excluded"])}
                for idx, v in result.items()}
    if stage == "s6_outreach_writer":
        return {"drafts": len(result)}
    return {}


def redact_event(conn, case_id: str, type_: str, payload: dict) -> dict:
    if type_ == "stage.done":
        stages = _stages(conn, case_id)
        return {"stage": payload["stage"], "result": redact_stage_result(case_id, payload["stage"], payload["result"], stages)}
    if type_ == "approval.requested":
        return {"outreach_id": payload["outreach_id"], "ref": expert_ref(case_id, payload["person_id"]),
                "persona": payload["persona"], "subquestion_indices": payload["subquestion_indices"]}
    if type_ == "mail.sent":
        return {"outreach_id": payload["outreach_id"]}
    if type_ in ("approval.approved", "approval.rejected", "mail.blocked", "mail.failed"):
        return {"outreach_id": payload["outreach_id"]}
    return payload


def customer_view(conn, case_id: str) -> dict:
    case = _case(conn, case_id)
    stages = _stages(conn, case_id)
    params = json.loads(case["params"])
    plan = stages.get("s2_decomposer")
    quote = None
    if plan:
        limit = config.dev_max_subquestions()
        quote = pricing.quote(len(plan if limit is None else plan[:limit]))
    names = _company_names(stages)
    final = stages.get("s5b_enrich_rerank") or stages.get("s5_ranker") or {}
    screening = {}
    for idx, screens in stages.get("s4_people_screen", {}).items():
        cands = {p["person_id"]: p for p in stages["s3_sourcer"][idx]["candidates"]}
        screening[idx] = {
            "considered": len(screens), **{k: sum(1 for s in screens if s["verdict"] == k) for k in ("pass", "review", "fail")},
            "excluded": [{"ref": expert_ref(case_id, s["person_id"]),
                          "reasons": [r["reason"] for r in s["results"] if not r["passed"]]}
                         for s in screens if s["verdict"] == "fail" and s["person_id"] in cands]}
    outreach = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) n FROM outreach WHERE case_id=? GROUP BY status", (case_id,))}
    return {
        "id": case["id"], "question": case["question"], "state": case["state"], "refusal_reason": case["refusal_reason"],
        "created_at": case["created_at"], "plan": plan, "quote": quote,
        "approval": {"panel_size": params["panel_size"]} if "panel_size" in params else None,
        "screening": screening,
        "panel": {idx: [card(case_id, p, names) for p in v["ranked"]] for idx, v in final.items()},
        "outreach": outreach, "invites": queue.invites(conn, case_id),
        "cost": costs(conn, case_id),
    }
