"""Stage 1: allow, refuse (with a reason) or rewrite the customer's question.

A rewrite must keep every company the question names: naming a company is not a reason to rewrite, and the
decomposer needs the name to target that company. The model lists the named companies; code keeps only names
that really appear in the question, and if a rewrite still drops one, code appends it to the rewritten question.
"""
import re

from ..core import llm

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["allow", "refuse", "rewrite"]},
        "reason": {"type": "string"},
        "rewritten_question": {"type": "string"},
        "named_companies": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "reason", "rewritten_question", "named_companies"],
}

SYSTEM = (
    "You screen business questions before an expert-network service researches them with former employees. "
    "REFUSE a question that asks for non-public or confidential information about a named company (for example "
    "unreleased financials, internal documents, material non-public information), asks to identify or contact "
    "a specific private individual, or is harmful or unrelated to business research. "
    "REWRITE when the question can be reframed into one answerable from public knowledge and first-hand experience "
    "without those problems; put the reframed question in rewritten_question. "
    "ALLOW otherwise. Naming a company is not by itself a reason to refuse or rewrite: asking what a company's "
    "former employees saw first-hand (demand, operations, pricing, competition) is allowed. If you rewrite, keep "
    "every company the question names. List in named_companies every company the question names, exactly as "
    "written in it. Always give a one-sentence reason. Leave rewritten_question empty unless rewriting."
)


def _in_text(name: str, text: str) -> bool:
    """Whole-word, case-insensitive match."""
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(name.strip())}(?![A-Za-z0-9])", text, re.I))


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
    named = [n.strip() for n in reply.get("named_companies") or [] if n.strip() and _in_text(n, question)]
    effective = reply["rewritten_question"].strip() if reply["verdict"] == "rewrite" else question
    restored = [n for n in named if not _in_text(n, effective)] if reply["verdict"] == "rewrite" else []
    if restored:  # the rewrite dropped a company the customer named: put it back so sourcing still targets it
        effective = f"{effective.rstrip()} (Companies named in the original question: {', '.join(restored)}.)"
    return {
        "verdict": reply["verdict"],
        "reason": reply["reason"].strip(),
        "effective_question": effective,
        "named_companies": named,
        "restored_companies": restored,
    }, call_id
