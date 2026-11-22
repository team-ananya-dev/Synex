"""Stage 5: score each screened candidate against the sub-question with the small model.

The model must back every score with exact snippets copied from the facts it was
given. Snippets are verified in code: an unsupported one is dropped, and a
candidate left with no supported evidence is capped and kept off the panel.
"""
from ..core import llm

MIN_SCORE = 40       # below this a candidate is left off the panel
UNSUPPORTED_CAP = 30  # score cap when no evidence snippet could be verified

SCHEMA = {
    "type": "object",
    "properties": {"ranked": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "person_id": {"type": "integer"},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
            "data_conflict": {"type": "string"},
        },
        "required": ["person_id", "score", "evidence", "reason", "data_conflict"],
    }}},
    "required": ["ranked"],
}

SYSTEM = (
    "You rate how well each former employee could answer a business sub-question from first-hand experience "
    "in the stated expertise. Score 0-100. Use ONLY the facts listed for each candidate; never assume what "
    "a job involved beyond what the title, description or skills say. "
    "evidence: 1 to 3 snippets copied EXACTLY (same words, same spelling) from that candidate's title, headline, "
    "function, role description or skills, the ones your score rests on. Copy only the value text, without labels "
    "such as 'title:'. Tenure, dates and employers are not evidence of expertise. reason: one line that uses only those snippets. "
    "data_conflict: if facts contradict each other (for example the headline describes an unrelated career "
    "from the job title), say so in one line, otherwise an empty string. Low scores for unrelated roles."
)


def facts_for(c: dict) -> str:
    """The only text the model sees about a candidate; evidence must be quoted from it."""
    parts = [f"title: {c['title']}", f"function: {c['function'] or 'unknown'}", f"headline: {c['headline'] or ''}",
             f"tenure: {c['tenure_months']} months", f"left: {c['end_date']}",
             f"now at: {', '.join(e for e in c['current_employers'] if e) or 'none listed'}"]
    if c.get("crustdata_fit"):
        parts.append(f"search relevance tier: {c['crustdata_fit']}")
    if c.get("role_description"):
        parts.append(f"role description: {c['role_description']}")
    if c.get("skills"):
        parts.append(f"skills: {', '.join(k for k in c['skills'] if k)}")
    return "; ".join(parts)


def evidence_source(c: dict) -> str:
    """Text a snippet may be quoted from: what says what the person did. Tenure, dates and employers do not count."""
    return " | ".join(str(x) for x in [c["title"], c["function"], c["headline"], c.get("role_description"),
                                      ", ".join(k for k in c.get("skills") or [] if k)] if x).lower()


def fit_label(score: int) -> str:
    return "strong" if score >= 70 else "partial" if score >= MIN_SCORE else "weak"


def rank(conn, candidates: list[dict], sub_question: str, expertise: str, case_id: str | None):
    """Return ({"ranked": [...], "excluded": [...]}, llm_call_id). ranked is the panel, best first."""
    if not candidates:
        return {"ranked": [], "excluded": []}, None
    ids = {c["person_id"] for c in candidates}

    def check(r):
        got = [x["person_id"] for x in r["ranked"]]
        if set(got) != ids or len(got) != len(ids):
            raise ValueError("score every candidate exactly once, using only the given person_ids")

    facts = {c["person_id"]: facts_for(c) for c in candidates}
    quotable = {c["person_id"]: evidence_source(c) for c in candidates}
    lines = "\n".join(f"- person_id {pid}: {f}" for pid, f in facts.items())
    reply, call_id = llm.call_json(
        conn, purpose="rank_candidates", case_id=case_id, validate=check, schema=SCHEMA, system=SYSTEM,
        user=f"Sub-question: {sub_question}\nExpertise needed: {expertise}\nCandidates:\n{lines}",
        max_tokens=2500,
    )
    by_id = {c["person_id"]: c for c in candidates}
    ranked, excluded = [], []
    for r in reply["ranked"]:
        text = quotable[r["person_id"]]
        evidence = [e.strip() for e in r["evidence"] if e.strip() and e.strip().lower() in text]
        score = r["score"] if evidence else min(r["score"], UNSUPPORTED_CAP)
        item = {**by_id[r["person_id"]], "score": score, "fit": fit_label(score), "evidence": evidence,
                "reason": r["reason"], "data_conflict": r["data_conflict"].strip(),
                "evidence_dropped": len(r["evidence"]) - len(evidence)}
        (ranked if score >= MIN_SCORE else excluded).append(item)
    ranked.sort(key=lambda x: -x["score"])
    excluded.sort(key=lambda x: -x["score"])
    return {"ranked": ranked, "excluded": [
        {"person_id": e["person_id"], "name": e["name"], "score": e["score"], "title": e["title"],
         "why": "no supported evidence" if not e["evidence"] else "low fit"} for e in excluded]}, call_id


def with_profile(candidate: dict, person_data: dict, company_id: int) -> dict:
    """Add the role description and skills from an enriched profile."""
    roles = [r for r in person_data.get("experience", {}).get("employment_details", {}).get("past", [])
             if r.get("crustdata_company_id") == company_id]
    role = max(roles, key=lambda r: r.get("end_date") or "") if roles else {}
    skills = (person_data.get("skills") or {}).get("professional_network_skills") or []
    return {**candidate, "role_description": (role.get("description") or "").strip()[:600], "skills": skills[:15]}
