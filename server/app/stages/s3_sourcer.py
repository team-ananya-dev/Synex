"""Stage 3: find former employees. Picks the company by id, then searches by id."""
from datetime import date, datetime

from ..core import llm
from ..crustdata import company as company_api
from ..crustdata import people as people_api
from ..crustdata.client import CrustdataClient

PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "company_id": {"type": "integer"},
        "reason": {"type": "string"},
        "confident": {"type": "boolean"},
    },
    "required": ["company_id", "reason", "confident"],
}


_NOISE = {"pvt", "ltd", "limited", "private", "inc", "llc", "corp", "corporation", "co", "company", "the", "india", "express", "courier"}


def _norm_name(name: str | None) -> str:
    words = "".join(ch.lower() if ch.isalnum() else " " for ch in (name or "")).split()
    return " ".join(w for w in words if w not in _NOISE)


def _size_floor(size: str | None) -> int:
    """Lower bound of Crustdata's employee range ("1001-5000" -> 1001, "10001+" -> 10001); 0 when not stated."""
    import re
    m = re.match(r"\s*(\d+)", size or "")
    return int(m.group(1)) if m else 0


def clear_winner(name: str, shortlist: list[dict]) -> dict | None:
    """The one record that is plainly the company called `name`: the only record with that name, or among several
    the one at least twice as large as the next. Several equally large records with the same name stay ambiguous."""
    wanted = _norm_name(name)
    same = [c for c in shortlist if wanted and _norm_name(c["name"]) == wanted]
    if len(same) == 1:
        return same[0]
    if len(same) > 1:
        ranked = sorted(same, key=lambda c: _size_floor(c["size"]), reverse=True)
        top, second = _size_floor(ranked[0]["size"]), _size_floor(ranked[1]["size"])
        if top >= 11 and top >= 2 * second:
            return ranked[0]
    return None


def resolve_company(conn, client: CrustdataClient, name: str, context: str, case_id: str | None):
    """Return (chosen candidate, all candidates, pick info). The model only chooses among ids Crustdata returned and
    the choice is validated in code. The question is background only: a competitor or peer is not "unsure" just
    because the question is about another company. If the model hedges but one record is plainly that company, code
    accepts it; genuinely ambiguous names (equal records sharing the name) stay ambiguous."""
    cands, _ = company_api.identify(client, name)
    if not cands:
        raise LookupError(f"no company found for {name!r}")
    shortlist = cands[:10]
    if len(shortlist) == 1:
        return shortlist[0], cands, {"method": "only_match", "confident": True}
    ids = {c["company_id"] for c in shortlist}

    def check(r):
        if r["company_id"] not in ids:
            raise ValueError("company_id must be one of the candidates")

    lines = "\n".join(
        f"- id {c['company_id']}: {c['name']} | {c['domain']} | founded {c['year_founded']} | size {c['size']} | "
        f"{', '.join(c['industries'][:3])} | {c['description']}" for c in shortlist)
    reply, call_id = llm.call_json(
        conn, purpose="resolve_company", case_id=case_id, validate=check, schema=PICK_SCHEMA,
        system="You pick which record is the company with the given name. Use only the listed ids. Choose the record that is "
               "clearly the main company of that name: a matching name, an official website, normally the largest. The question "
               "is background only: the company may be a competitor or peer being researched for comparison, so never judge "
               "the record by whether it fits the question, and never say confident=false because the question is about another "
               "company. Say confident=false only if two or more records could equally be this company, for example different "
               "companies that share the name.",
        user=f"Company to find: {name}\nBackground, the customer's question (do not match against it): {context}\nCandidates:\n{lines}",
    )
    chosen = next(c for c in shortlist if c["company_id"] == reply["company_id"])
    pick = {"method": "model", "llm_call_id": call_id, **reply}
    if not reply["confident"]:
        winner = clear_winner(name, shortlist)
        if winner is not None:
            chosen = winner
            pick = {"method": "name_match", "llm_call_id": call_id, "company_id": winner["company_id"], "confident": True,
                    "reason": f"the model hedged, but {winner['name']} is the only record that is plainly this company (matching name, clearly the largest)"}
    return chosen, cands, pick


def _months_between(a: str, b: str) -> int:
    d1, d2 = datetime.fromisoformat(a).date(), datetime.fromisoformat(b).date()
    return (d2.year - d1.year) * 12 + d2.month - d1.month


def normalise(profile: dict, company_id: int, call_id: str, today: date) -> dict:
    """Flatten one profile around its role at the target company."""
    emp = profile["experience"]["employment_details"]
    roles = [r for r in emp.get("past", []) if r.get("crustdata_company_id") == company_id and r.get("end_date")]
    role = max(roles, key=lambda r: r["end_date"]) if roles else {}
    role_path = f"experience.employment_details.past[{emp['past'].index(role)}]" if role else None
    current = emp.get("current", [])
    return {
        "person_id": profile["crustdata_person_id"],
        "name": profile["basic_profile"]["name"],
        "headline": profile["basic_profile"].get("headline"),
        "location": (profile["basic_profile"].get("location") or {}).get("raw"),
        "country": (profile["basic_profile"].get("location") or {}).get("country"),
        "profile_url": ((profile.get("social_handles") or {}).get("professional_network_identifier") or {}).get("profile_url"),
        "title": role.get("title"),
        "function": role.get("function_category"),
        "start_date": (role.get("start_date") or "")[:10] or None,
        "end_date": (role.get("end_date") or "")[:10] or None,
        "tenure_months": _months_between(role["start_date"], role["end_date"]) if role.get("start_date") else None,
        "still_at_company": any(c.get("crustdata_company_id") == company_id for c in current),
        "current_employers": [c.get("name") for c in current if c.get("name")],
        "current_roles": [{"company_id": c.get("crustdata_company_id"), "name": c.get("name"), "website": c.get("company_website"),
                           "title": c.get("title"), "seniority": c.get("seniority_level"),
                           "path": f"experience.employment_details.current[{i}]"} for i, c in enumerate(current)],
        "role_path": role_path,   # where the target-company role sits in the Crustdata person record
        "crustdata_fit": profile.get("fit"),
        "record_updated_at": (profile.get("metadata") or {}).get("updated_at"),
        "source_call_id": call_id,
    }


def source(conn, client, company_id: int, today: date, min_left: int, max_left: int, min_years: int, limit: int = 25,
           title_any: list[str] | None = None, query: str | None = None):
    profiles, meta, call_id = people_api.search_former_employees(client, company_id, today, min_left, max_left, min_years, limit, title_any, query)
    return [normalise(p, company_id, call_id, today) for p in profiles], meta, call_id
