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


def resolve_company(conn, client: CrustdataClient, name: str, context: str, case_id: str | None):
    """Return (chosen candidate, all candidates, pick info). The model only chooses among ids Crustdata returned and
    the choice is validated in code. The question is background only: a competitor or peer is not "unsure" just
    because the question is about another company; the model is unsure only when records of different companies
    share the name. The runner never guesses: an unsure pick is reported as ambiguous and not searched."""
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
        system="You pick which record is the company with the given name. Use only the listed ids. A record is a match when its "
               "name and website fit the name asked for. The question is background: never reject a record because the question "
               "is about a different company (the company may be a competitor or peer researched for comparison). But when "
               "several records share the name or start with it and belong to clearly different companies (for example Apollo "
               "Hospitals and Apollo Tyres), use the question's industry and country only to break the tie, and say confident=false "
               "if it still does not settle which one is meant. Do not pick a record just because it is the largest or most "
               "prominent. Say confident=true only when one record is clearly the company asked for.",
        user=f"Company to find: {name}\nBackground, the customer's question (do not match against it): {context}\nCandidates:\n{lines}",
    )
    chosen = next(c for c in shortlist if c["company_id"] == reply["company_id"])
    return chosen, cands, {"method": "model", "llm_call_id": call_id, **reply}


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
