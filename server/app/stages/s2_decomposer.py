"""Stage 2: split a business question into sub-questions a former employee could answer.

Each sub-question carries the expertise needed, short job-title phrases for the
sourcer, and target companies. A company is "named" when it appears in the
question (checked in code) and "inferred" otherwise. The stage knows no company.
"""
from ..core import llm

SCHEMA = {
    "type": "object",
    "properties": {
        "subquestions": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "expertise": {"type": "string"},
                "title_keywords": {"type": "array", "items": {"type": "string"}},
                "target_companies": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "basis": {"type": "string", "enum": ["named", "inferred"]},
                    },
                    "required": ["name", "basis"],
                }},
            },
            "required": ["text", "expertise", "title_keywords", "target_companies"],
        }},
    },
    "required": ["subquestions"],
}

SYSTEM = (
    "You plan expert interviews. Split the customer's question into 3 to 5 sub-questions. "
    "Each must be answerable from first-hand experience by a former employee, and must not ask for "
    "non-public or confidential information. For each give: the expertise needed; 2 to 6 short job-title "
    "phrases (1 to 3 words, such as 'operations' or 'supply chain') that people with that expertise hold; "
    "and target companies whose former employees to approach. Mark a company 'named' only if the question "
    "itself mentions it; otherwise 'inferred' (for example a direct competitor). If the question names no "
    "company, infer 2 to 4 relevant ones. Use only what the question implies; do not invent facts."
)


def validate(question: str, reply: dict) -> None:
    subs = reply["subquestions"]
    if not 3 <= len(subs) <= 5:
        raise ValueError("return between 3 and 5 sub-questions")
    q = question.lower()
    for i, s in enumerate(subs, 1):
        if not s["text"].strip() or not s["expertise"].strip():
            raise ValueError(f"sub-question {i} has empty text or expertise")
        kws = [k.strip() for k in s["title_keywords"] if k.strip()]
        if not 2 <= len(kws) <= 6:
            raise ValueError(f"sub-question {i} needs 2 to 6 non-empty title phrases")
        if any(len(k.split()) > 3 for k in kws):
            raise ValueError(f"sub-question {i}: title phrases must be at most 3 words")
        if not s["target_companies"]:
            raise ValueError(f"sub-question {i} needs at least one target company")
        for c in s["target_companies"]:
            if c["basis"] == "named" and c["name"].lower() not in q:
                raise ValueError(f"{c['name']!r} is marked named but is not in the question; mark it inferred")


def decompose(conn, question: str, case_id: str | None) -> tuple[list[dict], str]:
    reply, call_id = llm.call_json(
        conn, purpose="decompose_question", case_id=case_id, schema=SCHEMA, system=SYSTEM,
        user=f"Customer question: {question}", max_tokens=2000,
        validate=lambda r: validate(question, r),
    )
    subs = []
    for i, s in enumerate(reply["subquestions"], 1):
        subs.append({
            "index": i,
            "text": s["text"].strip(),
            "expertise": s["expertise"].strip(),
            "title_keywords": [k.strip() for k in s["title_keywords"] if k.strip()],
            "target_companies": s["target_companies"],
        })
    return subs, call_id
