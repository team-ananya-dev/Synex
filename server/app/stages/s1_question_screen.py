"""Stage 1: allow, refuse (with a reason) or rewrite the customer's question."""
from ..core import llm

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["allow", "refuse", "rewrite"]},
        "reason": {"type": "string"},
        "rewritten_question": {"type": "string"},
    },
    "required": ["verdict", "reason", "rewritten_question"],
}

SYSTEM = (
    "You screen business questions before an expert-network service researches them with former employees. "
    "REFUSE a question that asks for non-public or confidential information about a named company (for example "
    "unreleased financials, internal documents, material non-public information), asks to identify or contact "
    "a specific private individual, or is harmful or unrelated to business research. "
    "REWRITE when the question can be reframed into one answerable from public knowledge and first-hand experience "
    "without those problems; put the reframed question in rewritten_question. "
    "ALLOW otherwise. Always give a one-sentence reason. Leave rewritten_question empty unless rewriting."
)


def validate(reply: dict) -> None:
    if not reply["reason"].strip():
        raise ValueError("give a reason")
    if reply["verdict"] == "rewrite" and not reply["rewritten_question"].strip():
        raise ValueError("a rewrite needs rewritten_question")


def screen(conn, question: str, case_id: str | None) -> tuple[dict, str]:
    reply, call_id = llm.call_json(
        conn, purpose="screen_question", case_id=case_id, schema=SCHEMA, system=SYSTEM,
        user=f"Customer question: {question}", validate=validate,
    )
    return {
        "verdict": reply["verdict"],
        "reason": reply["reason"].strip(),
        "effective_question": reply["rewritten_question"].strip() if reply["verdict"] == "rewrite" else question,
    }, call_id
