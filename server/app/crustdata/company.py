"""Company identification. A name can match many unrelated companies, so the
caller must pick one by id and keep the alternatives."""
from .client import CrustdataClient


def identify(client: CrustdataClient, name: str, case_id_purpose: str = "identify_company") -> tuple[list[dict], str]:
    data, call_id = client.post("/company/identify", {"names": [name]}, case_id_purpose)
    out = []
    for m in (data[0]["matches"] if data else []):
        b = m["company_data"]["basic_info"]
        out.append({
            "company_id": b["crustdata_company_id"],
            "name": b.get("name"),
            "domain": b.get("primary_domain"),
            "year_founded": b.get("year_founded"),
            "size": b.get("employee_count_range"),
            "industries": b.get("industries") or [],
            "description": (b.get("description") or "")[:240],
            "confidence": m.get("confidence_score"),
        })
    return out, call_id


def _host(url: str) -> str:
    u = url.strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    u = u.split("/")[0]
    return u[4:] if u.startswith("www.") else u


def competitors(client: CrustdataClient, company_id: int) -> tuple[list[str], str]:
    """Direct competitors by website domain, from Crustdata's paid and organic search competitor lists
    (2 credits). The wider all_domains list is not used: it is full of unrelated sites."""
    data, call_id = client.post(
        "/company/enrich", {"crustdata_company_ids": [company_id], "fields": ["competitors"]}, "competitor_check")
    comp = data[0]["matches"][0]["company_data"].get("competitors") or {} if data and data[0].get("matches") else {}
    hosts = {_host(d) for key in ("organic_seo", "paid_seo") for d in comp.get(key) or [] if d.strip()}
    return sorted(h for h in hosts if h), call_id
