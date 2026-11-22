"""Give each invited expert a fixed small number of questions, matched to their experience.

Stage 6 first picks who to invite for each sub-question. Left alone, that gives most experts a single question.
This step then tops every invited expert up to QUESTIONS_PER_EXPERT questions (default 3, never more than the plan
has): their own question(s) first, then the other sub-questions they are best placed to answer from first-hand
experience. The expert can still answer, say "I don't know" or say "I can't answer without sharing confidential
information" on each one.

One small-model call per case lists, for each expert, the sub-questions that fit their role, function, tenure and
why they fit (never a name). Code takes that list in order and fills any shortfall by a plain rule: the
sub-question where the expert ranked best, then plan order. The number of questions per expert is fixed by code,
never by the model, so a weak or missing model reply cannot change it.
"""
import os

from .core import llm
from .core.events import append_event

DEFAULT_PER_EXPERT = 3
MAX_PER_EXPERT = 5


def questions_per_expert() -> int:
    try:
        n = int(os.environ.get("SYNEX_QUESTIONS_PER_EXPERT", DEFAULT_PER_EXPERT))
    except ValueError:
        n = DEFAULT_PER_EXPERT
    return max(1, min(MAX_PER_EXPERT, n))


SCHEMA = {
    "type": "object",
    "properties": {"assignments": {"type": "array", "items": {
        "type": "object",
        "properties": {"person_id": {"type": "integer"}, "subquestions": {"type": "array", "items": {"type": "integer"}}},
        "required": ["person_id", "subquestions"],
    }}},
    "required": ["assignments"],
}

SYSTEM = (
    "You match interview questions to former employees. For each expert, list the sub-questions they could answer from "
    "first-hand experience, best fit first, judging only from the role, function, tenure, skills and reason given. "
    "List every sub-question that plausibly fits, not just the ones already assigned: more than one is expected. "
    "Never list a sub-question their role could not know first-hand. Use only the sub-question numbers given."
)


def _score(panels: dict[str, list[dict]], idx: int, person_id: int) -> int:
    for p in panels.get(str(idx), []):
        if p["person_id"] == person_id:
            return int(p.get("score") or 0)
    return -1


def fallback_extras(person_id: int, taken: list[int], all_indices: list[int], k: int, panels: dict) -> list[int]:
    """Extras by rule, as many as still needed to reach k: where this expert ranked best, then plan order."""
    others = [i for i in all_indices if i not in taken]
    others.sort(key=lambda i: (-_score(panels, i, person_id), i))
    return others[: max(0, k - len(taken))]


def validate(reply: dict, wanted: dict[int, list[int]], valid: set[int]) -> None:
    """The reply is a preference list per expert; the count is decided by code, so only malformed replies are rejected."""
    seen = set()
    for a in reply["assignments"]:
        if a["person_id"] not in wanted:
            raise ValueError(f"unknown expert {a['person_id']}; use only {sorted(wanted)}")
        if a["person_id"] in seen:
            raise ValueError(f"expert {a['person_id']} appears twice")
        seen.add(a["person_id"])
        if len(set(a["subquestions"])) != len(a["subquestions"]) or not set(a["subquestions"]) <= valid:
            raise ValueError(f"expert {a['person_id']}: use each of {sorted(valid)} at most once")


def assign(conn, case_id: str, chosen: dict[int, dict], subs: list[dict], panels: dict[str, list[dict]], k: int | None = None) -> str:
    """Extend each chosen[person_id]["subs"] in place. Returns "model", "rule" or "none"."""
    k = min(k if k is not None else questions_per_expert(), len(subs))
    if k <= 1 or not chosen:
        return "none"
    by_index = {s["index"]: s for s in subs}
    valid = set(by_index)
    primaries = {pid: sorted(s["index"] for s in e["subs"]) for pid, e in chosen.items()}

    extras: dict[int, list[int]] = {}
    preferred: dict[int, list[int]] = {}
    method = "rule"
    try:
        lines = []
        for pid, e in chosen.items():
            p = e["person"]
            lines.append(
                f"- expert {pid}: role {p.get('title')!r}; function {p.get('function') or 'unknown'}; "
                f"{p.get('tenure_months')} months; why they fit: {p.get('reason')}; "
                f"role description: {(p.get('role_description') or 'none')[:240]!r}; skills: {', '.join((p.get('skills') or [])[:8]) or 'none'}; "
                f"primary sub-questions: {primaries[pid]}")
        questions = "\n".join(f"{s['index']}. {s['text']} (expertise: {s['expertise']})" for s in subs)
        reply, _ = llm.call_json(
            conn, purpose="assign_questions", case_id=case_id, schema=SCHEMA, system=SYSTEM, max_tokens=1500,
            validate=lambda r: validate(r, primaries, valid),
            user=f"Sub-questions:\n{questions}\n\nExperts:\n" + "\n".join(lines))
        preferred = {a["person_id"]: a["subquestions"] for a in reply["assignments"]}
        method = "model"
    except Exception:   # invalid reply twice, budget reached, network: the rule decides
        preferred = {}
    filled = False
    for pid in chosen:
        need = max(0, k - len(primaries[pid]))
        picks = [i for i in preferred.get(pid, []) if i not in primaries[pid]][:need]
        if len(picks) < need:   # the model gave too few (or nothing): fill by rule, so the count is always fixed
            picks += fallback_extras(pid, primaries[pid] + picks, sorted(valid), k, panels)
            filled = True
        extras[pid] = picks
    if not any(preferred.get(pid) for pid in chosen):
        method = "rule"
    elif filled:
        method = "model+rule"
    for pid, e in chosen.items():
        order = primaries[pid] + extras.get(pid, [])
        e["subs"] = [by_index[i] for i in order]
    append_event(conn, case_id, "questions.assigned", {
        "experts": len(chosen), "questions_per_expert": k, "method": method,
        "questions_total": sum(len(e["subs"]) for e in chosen.values())})
    return method
