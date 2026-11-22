"""Person search for former employees of one company, identified by id."""
from datetime import date

from .client import CrustdataClient

EMP = "experience.employment_details"


def months_before(today: date, months: int) -> date:
    y, m = divmod(today.year * 12 + today.month - 1 - months, 12)
    return date(y, m + 1, min(today.day, 28))


def search_former_employees(
    client: CrustdataClient, company_id: int, today: date, min_left: int, max_left: int, min_years: int, limit: int = 25,
    title_any: list[str] | None = None, query: str | None = None,
) -> tuple[list[dict], dict, str]:
    """Roles are matched as one element: the same role must be at the company, end in
    the window and have the minimum tenure. Returns (profiles, meta, call_id)."""
    body = {"filters": {"op": "and", "conditions": [
        {"field": f"{EMP}.company_id", "type": "=", "value": company_id},
        {"field": f"{EMP}.end_date", "type": "=>", "value": months_before(today, max_left).isoformat()},
        {"field": f"{EMP}.end_date", "type": "=<", "value": months_before(today, min_left).isoformat()},
        {"field": f"{EMP}.years_at_company_raw", "type": "=>", "value": min_years},
        # people still listed at the company changed roles inside it; they never left
        {"field": f"{EMP}.current.company_id", "type": "!=", "value": company_id},
    ]}, "limit": limit}
    if query:  # rank by relevance inside the hard filters ("exact" keeps every filter a hard constraint)
        body["search"] = {"query": query, "mode": "hybrid"}
        body["mode"] = "exact"
    if title_any:  # the same role must also have one of these phrases in its title
        body["filters"]["conditions"].append(
            {"op": "or", "conditions": [{"field": f"{EMP}.title", "type": "[.]", "value": t} for t in title_any]})
    data, call_id = client.post("/person/search", body, "source_former_employees")
    return data["profiles"], {"total_count": data.get("total_count")}, call_id


def enrich_people(client: CrustdataClient, profile_urls: list[str]) -> tuple[dict[str, dict], str | None]:
    """Full employment history (with role descriptions) and skills, 1 credit per person.
    Returns ({profile_url: person_data}, call_id)."""
    if not profile_urls:
        return {}, None
    data, call_id = client.post(
        "/person/enrich", {"professional_network_profile_urls": profile_urls, "fields": ["experience", "skills"]},
        "enrich_shortlist")
    out = {}
    for entry in data:
        for m in entry.get("matches") or []:
            out[entry["matched_on"]] = m["person_data"]
            break
    return out, call_id
