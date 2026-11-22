"""Case job runner: stages 1 to 5, one background job per case.

Every stage emits stage.started and stage.done (with its result) on the audit
chain; the stream route replays those events to the browser. Stage 6 (outreach)
does not exist yet, so a finished run ends with job.paused, not a state it has
not reached.
"""
import json
import uuid
from datetime import date, datetime, timezone

from ..core import config, db, llm
from ..core.events import append_event
from ..crustdata import people as people_api
from ..crustdata.client import CrustdataClient
from ..stages import s1_question_screen, s2_decomposer, s3_sourcer, s4_people_screen, s5_ranker

DEFAULT_PARAMS = {"min_left": 6, "max_left": 24, "min_years": 1}
CREDIT_CAP = 25.0
crustdata_transport = None  # tests only: an httpx transport that replaces the network


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_case(conn, question: str, params: dict | None = None) -> str:
    case_id = uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO cases (id, question, state, params, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (case_id, question, "DRAFT", json.dumps(params or DEFAULT_PARAMS), _now(), _now()),
    )
    conn.commit()
    append_event(conn, case_id, "case.created", {"question": question})
    return case_id


def set_state(conn, case_id: str, state: str, **extra) -> None:
    conn.execute("UPDATE cases SET state=?, updated_at=?, refusal_reason=COALESCE(?, refusal_reason) WHERE id=?",
                 (state, _now(), extra.get("reason") if state == "REFUSED" else None, case_id))
    conn.commit()
    append_event(conn, case_id, "case.state", {"state": state, **extra})


class StageFailed(RuntimeError):
    pass


def run_stage(conn, case_id: str, stage: str, fn):
    append_event(conn, case_id, "stage.started", {"stage": stage})
    try:
        result = fn()
    except Exception as e:
        append_event(conn, case_id, "stage.failed", {"stage": stage, "error": f"{type(e).__name__}: {e}"})
        raise StageFailed(f"{stage}: {e}") from e
    conn.execute("INSERT INTO stage_results (case_id, stage, result, created_at) VALUES (?,?,?,?)",
                 (case_id, stage, json.dumps(result, default=str), _now()))
    conn.commit()
    append_event(conn, case_id, "stage.done", {"stage": stage, "result": result})
    return result


def run_case(case_id: str) -> None:
    conn = db.connect()
    try:
        _run(conn, case_id)
    except StageFailed:
        set_state(conn, case_id, "FAILED")
    except Exception as e:  # nothing may leave a case stuck in a running state
        append_event(conn, case_id, "stage.failed", {"stage": "runner", "error": f"{type(e).__name__}: {e}"})
        set_state(conn, case_id, "FAILED")
    finally:
        conn.close()


def _run(conn, case_id: str) -> None:
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    params = json.loads(case["params"])
    today = date.today()

    screen = run_stage(conn, case_id, "s1_question_screen",
                       lambda: s1_question_screen.screen(conn, case["question"], case_id)[0])
    if screen["verdict"] == "refuse":
        set_state(conn, case_id, "REFUSED", reason=screen["reason"])
        return
    question = screen["effective_question"]

    subs = run_stage(conn, case_id, "s2_decomposer", lambda: s2_decomposer.decompose(conn, question, case_id)[0])
    set_state(conn, case_id, "PLANNED")
    set_state(conn, case_id, "SOURCING")

    client = CrustdataClient(conn, case_id=case_id, credit_cap=CREDIT_CAP, transport=crustdata_transport)
    limit = config.dev_max_subquestions()
    work = subs if limit is None else subs[:limit]

    def source_all():
        out = {}
        for sq in work:
            companies, people, seen = [], [], set()
            for target in sq["target_companies"][: config.max_companies_per_subquestion()]:
                try:
                    chosen, cands, pick = s3_sourcer.resolve_company(
                        conn, client, target["name"], f"{question} | {sq['text']}", case_id)
                except LookupError:
                    companies.append({"asked": target["name"], "basis": target["basis"], "resolved": False})
                    continue
                found, meta, call_id = s3_sourcer.source(
                    conn, client, chosen["company_id"], today, **params, limit=25, query=f"{sq['expertise']}: {sq['text']}")
                companies.append({"asked": target["name"], "basis": target["basis"], "resolved": True, "chosen": chosen,
                                  "alternatives": len(cands) - 1, "pick": pick, "total_matches": meta["total_count"],
                                  "search_call_id": call_id})
                for p in found:
                    if p["person_id"] not in seen:
                        seen.add(p["person_id"])
                        people.append({**p, "company_id": chosen["company_id"]})
            out[str(sq["index"])] = {"companies": companies, "candidates": people}
        return out

    sourced = run_stage(conn, case_id, "s3_sourcer", source_all)

    screens = run_stage(conn, case_id, "s4_people_screen", lambda: {
        idx: [s4_people_screen.screen(p, today, params) for p in v["candidates"]] for idx, v in sourced.items()})

    def rank_all():
        out = {}
        for sq in work:
            idx = str(sq["index"])
            verdict = {s["person_id"]: s["verdict"] for s in screens[idx]}
            kept = [{**p, "verdict": verdict[p["person_id"]]} for p in sourced[idx]["candidates"]
                    if verdict[p["person_id"]] != "fail"]
            result, call_id = s5_ranker.rank(conn, kept, sq["text"], sq["expertise"], case_id)
            out[idx] = {**result, "llm_call_id": call_id}
        return out

    ranked = run_stage(conn, case_id, "s5_ranker", rank_all)

    def enrich_all():
        """Fetch the full profile of the top few per sub-question and re-rank them on role descriptions and skills."""
        out = {}
        for sq in work:
            idx = str(sq["index"])
            first = ranked[idx]["ranked"]
            top, rest = first[: config.enrich_top()], first[config.enrich_top():]
            people, enrich_call = people_api.enrich_people(client, [p["profile_url"] for p in top if p["profile_url"]])
            enriched = [s5_ranker.with_profile(p, people[p["profile_url"]], p["company_id"])
                        if p["profile_url"] in people else p for p in top]
            result, llm_call = s5_ranker.rank(conn, enriched, sq["text"], sq["expertise"], case_id)
            out[idx] = {
                "ranked": sorted(result["ranked"] + rest, key=lambda x: -x["score"]),
                "excluded": ranked[idx]["excluded"] + result["excluded"],
                "enriched_person_ids": [p["person_id"] for p in enriched if p.get("role_description") is not None],
                "enrich_call_id": enrich_call, "llm_call_id": llm_call,
            }
        return out

    run_stage(conn, case_id, "s5b_enrich_rerank", enrich_all)
    append_event(conn, case_id, "job.paused", {"reason": "stage 6 (outreach) is not implemented yet"})
