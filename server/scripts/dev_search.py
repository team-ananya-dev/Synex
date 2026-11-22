"""Development check of Crustdata person search: left a company N to M months ago, minimum tenure.

Usage: python scripts/dev_search.py "<company>" [--min-left 6] [--max-left 24] [--min-years 1]
Goes through the logging client, so the call, its credits and the audit event are recorded.
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db  # noqa: E402
from app.crustdata.client import CrustdataClient  # noqa: E402

EMP = "experience.employment_details"


def months_before(today: date, months: int) -> date:
    y, m = divmod(today.year * 12 + today.month - 1 - months, 12)
    return date(y, m + 1, min(today.day, 28))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("company")
    ap.add_argument("--min-left", type=int, default=6)
    ap.add_argument("--max-left", type=int, default=24)
    ap.add_argument("--min-years", type=int, default=1)
    a = ap.parse_args()

    today = date.today()
    newest, oldest = months_before(today, a.min_left), months_before(today, a.max_left)
    body = {"filters": {"op": "and", "conditions": [
        {"field": f"{EMP}.company_name", "type": "=", "value": a.company},
        {"field": f"{EMP}.end_date", "type": "=>", "value": oldest.isoformat()},
        {"field": f"{EMP}.end_date", "type": "=<", "value": newest.isoformat()},
        {"field": f"{EMP}.years_at_company_raw", "type": "=>", "value": a.min_years},
    ]}}
    conn = db.connect()
    client = CrustdataClient(conn, case_id="dev-search")
    data, call_id = client.post("/person/search", body, "dev_search")
    print(f"call {call_id}: total_count={data.get('total_count')} returned={len(data['profiles'])} "
          f"window {oldest}..{newest} spent={client.credits_spent():.2f} credits")
    for p in data["profiles"]:
        roles = p["experience"]["employment_details"].get("past", [])
        hit = [r for r in roles if a.company.lower() in (r.get("name") or "").lower()
               and r.get("end_date") and oldest <= datetime.fromisoformat(r["end_date"]).date() <= newest]
        r = hit[0] if hit else {}
        cur = [c["name"] for c in p["experience"]["employment_details"].get("current", [])]
        print(f"- {p['basic_profile']['name']} | {r.get('title')} | fn={r.get('function_category')} | "
              f"{(r.get('start_date') or '')[:7]} to {(r.get('end_date') or '')[:7]} "
              f"({r.get('years_at_company_raw')}y) | now: {cur or 'none'}")


main()
