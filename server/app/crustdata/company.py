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
