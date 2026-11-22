"""Stage 5: score each screened candidate against the sub-question with the small model."""
from ..core import llm

SCHEMA = {
    "type": "object",
    "properties": {"ranked": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "person_id": {"type": "integer"},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "reason": {"type": "string"},
        },
        "required": ["person_id", "score", "reason"],
    }}},
    "required": ["ranked"],
}


def rank(conn, candidates: list[dict], sub_question: str, expertise: str, case_id: str | None):
    if not candidates:
        return [], None
    ids = {c["person_id"] for c in candidates}

    def check(r):
        got = [x["person_id"] for x in r["ranked"]]
        if set(got) != ids or len(got) != len(ids):
            raise ValueError("score every candidate exactly once, using only the given person_ids")

    lines = "\n".join(
        f"- person_id {c['person_id']}: role {c['title']!r} (function {c['function'] or 'unknown'}), "
        f"{c['tenure_months']} months, left {c['end_date']}, headline {c['headline']!r}, now at {c['current_employers'] or 'none listed'}"
        for c in candidates)
    reply, call_id = llm.call_json(
        conn, purpose="rank_candidates", case_id=case_id, validate=check, schema=SCHEMA,
        system="You rate how well each former employee could answer a business sub-question from first-hand "
               "experience in the stated expertise. Score 0-100. Use only the facts given; do not guess beyond them. "
               "Give a one-line reason that cites the facts. Low scores for roles unrelated to the expertise.",
        user=f"Sub-question: {sub_question}\nExpertise needed: {expertise}\nCandidates:\n{lines}",
    )
    by_id = {c["person_id"]: c for c in candidates}
    ranked = sorted(reply["ranked"], key=lambda r: -r["score"])
    return [{**by_id[r["person_id"]], "score": r["score"], "reason": r["reason"]} for r in ranked], call_id
