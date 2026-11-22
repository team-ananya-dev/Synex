"""Development run of stages 3 to 5 for any company.

Usage: python scripts/dev_pipeline.py "<company>" "<sub-question>" "<expertise>" [--context "<question>"]
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db, llm  # noqa: E402
from app.crustdata.client import CrustdataClient  # noqa: E402
from app.stages import s3_sourcer, s4_people_screen, s5_ranker  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("company")
ap.add_argument("sub_question")
ap.add_argument("expertise")
ap.add_argument("--context", default="")
ap.add_argument("--title", action="append", help="title phrase; repeat for several")
ap.add_argument("--min-left", type=int, default=6)
ap.add_argument("--max-left", type=int, default=24)
ap.add_argument("--min-years", type=int, default=1)
a = ap.parse_args()
params = {"min_left": a.min_left, "max_left": a.max_left, "min_years": a.min_years}
today = date.today()
case = "dev-pipeline"

conn = db.connect()
client = CrustdataClient(conn, case_id=case)
chosen, cands, pick = s3_sourcer.resolve_company(conn, client, a.company, a.context or a.sub_question, case)
print(f"company: {chosen['name']} ({chosen['domain']}, id {chosen['company_id']}, size {chosen['size']}) "
      f"picked by {pick['method']}; {len(cands)} candidates; {pick.get('reason', '')}")
people, meta, call_id = s3_sourcer.source(conn, client, chosen["company_id"], today, **params, limit=25, title_any=a.title)
print(f"search call {call_id}: {meta['total_count']} match, {len(people)} fetched")

screens = {p["person_id"]: s4_people_screen.screen(p, today, params) for p in people}
kept = [p for p in people if screens[p["person_id"]]["verdict"] != "fail"]
for p in people:
    s = screens[p["person_id"]]
    if s["verdict"] == "fail":
        why = "; ".join(r["reason"] for r in s["results"] if not r["passed"])
        print(f"  FAIL {p['name']}: {why}")
ranked, rank_call = s5_ranker.rank(conn, kept, a.sub_question, a.expertise, case)
for r in ranked:
    flag = " [review]" if screens[r["person_id"]]["verdict"] == "review" else ""
    print(f"{r['score']:3d}  {r['name']} | {r['title']} | {r['tenure_months']}m | left {r['end_date']}{flag}\n       {r['reason']}")
print(f"credits spent: {client.credits_spent():.2f} | model spend: ${llm.spent_usd(conn):.4f}")
