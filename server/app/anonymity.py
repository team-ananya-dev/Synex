"""Anonymity rule for what the customer sees next to an answer.

Site flow and build guide: if fewer than 3 accepted experts in a case share a role label, the label is coarsened
so one person cannot be picked out from it. The coarse label keeps only a seniority band and a broad function,
for example "Senior operations leader" or "Sales manager". Applied in code to the customer responses route and
the stage 8 result; the expert's own page and the operator screens keep the exact title.
"""
import re

MIN_SHARED = 3

_SENIORITY = [
    ("senior leader", r"\b(chief|ceo|cfo|coo|cto|cmo|cxo|vp|vice president|president|head|director|general manager|gm|founder|partner)\b"),
    ("manager", r"\b(manager|mgr|lead|supervisor|asm|rsm|zonal|regional|area|in-charge|incharge)\b"),
    ("specialist", r"\b(analyst|engineer|specialist|associate|executive|consultant|designer|developer|officer|coordinator|scientist)\b"),
]
_FUNCTION = [
    ("supply chain", r"\b(supply|logistics|warehouse|procurement|sourcing|fulfil\w*|inventory|purchas\w*)\b"),
    ("store operations", r"\b(store|shift|barista|restaurant|outlet|cafe|café)\b"),
    ("sales", r"\b(sales|business development|bd|account|territory|asm|rsm|revenue|channel)\b"),
    ("marketing", r"\b(marketing|brand|growth|content|communications|pr)\b"),
    ("customer experience", r"\b(customer|cx|support|loyalty|service|experience)\b"),
    ("product", r"\b(product)\b"),
    ("technology", r"\b(engineer\w*|developer|software|tech\w*|data|it|devops|security)\b"),
    ("finance", r"\b(finance|financial|accounting|accountant|controller|treasury|audit|fp&a)\b"),
    ("strategy", r"\b(strategy|strategic|planning|pricing|business|consult\w*|transformation)\b"),
    ("people", r"\b(hr|human resources|talent|recruit\w*|people)\b"),
    ("operations", r"\b(operations|ops|operational)\b"),
]


def coarse_role(title: str | None) -> str:
    t = (title or "").lower()
    seniority = next((name for name, rx in _SENIORITY if re.search(rx, t)), None)
    function = next((name for name, rx in _FUNCTION if re.search(rx, t)), None)
    if seniority == "senior leader":
        return f"Senior {function} leader" if function else "Senior leader"
    if seniority == "manager":
        return f"{function.capitalize()} manager" if function else "Manager"
    if seniority == "specialist":
        return f"{function.capitalize()} specialist" if function else "Specialist"
    return f"{function.capitalize()} team member" if function else "Former employee"


def _key(title: str | None) -> str:
    return " ".join((title or "").split()).lower()


def anonymise_roles(answers: list[dict], person_key: str = "person_id") -> None:
    """Replace each answer's "role" in place. An exact title stays only if at least MIN_SHARED different
    experts with that title have accepted answers in this case; otherwise the coarse label is shown."""
    holders: dict[str, set] = {}
    for a in answers:
        holders.setdefault(_key(a.get("role")), set()).add(a.get(person_key))
    for a in answers:
        if len(holders.get(_key(a.get("role")), ())) < MIN_SHARED:
            a["role"] = coarse_role(a.get("role"))
