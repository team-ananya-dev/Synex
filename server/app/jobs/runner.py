"""Case job runner: stages 1 to 6, in two background phases per case.

Phase 1 (run_case) screens the question and plans, then waits at PLANNED for the customer to
approve the plan and the spend. Phase 2 (continue_case) sources, screens, ranks, enriches and
drafts outreach, then waits at AWAITING_APPROVAL for the customer to review the anonymised invitations and approve them.
Every stage emits stage.started and stage.done (with its result) on the audit chain; the stream
routes replay those events to the browser.
"""
import json
import uuid
from datetime import date, datetime, timezone

from ..core import config, db, llm
from ..core.events import append_event
from ..crustdata import company as company_api
from ..crustdata import people as people_api
from ..crustdata.client import CrustdataClient
from ..stages import s1_question_screen, s2_decomposer, s3_sourcer, s4_people_screen, s5_ranker, s6_outreach_writer

DEFAULT_PARAMS = {"min_left": 6, "max_left": 24, "min_years": 1}
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
    """Run one stage, or reuse its stored result if it already finished (after a crash or a retry), so no
    finished stage spends credits or sends anything twice."""
    done = conn.execute("SELECT result FROM stage_results WHERE case_id=? AND stage=? ORDER BY id DESC LIMIT 1",
                        (case_id, stage)).fetchone()
    if done:
        append_event(conn, case_id, "stage.reused", {"stage": stage})
        return json.loads(done["result"])
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


def _guarded(case_id: str, phase) -> None:
    conn = db.connect()
    try:
        phase(conn, case_id)
    except StageFailed:
        set_state(conn, case_id, "FAILED")
    except Exception as e:  # nothing may leave a case stuck in a running state
        append_event(conn, case_id, "stage.failed", {"stage": "runner", "error": f"{type(e).__name__}: {e}"})
        set_state(conn, case_id, "FAILED")
    finally:
        conn.close()


def resume_on_startup() -> None:
    """After a restart: finish approved-but-unsent invitations, then continue every case that was mid-run, from its
    last finished stage. A case stuck in SOURCING without a plan approval predates that step and cannot resume."""
    import threading
    from ..actions import queue
    conn = db.connect()
    try:
        for cid in queue.resume_sends(conn):
            if conn.execute("SELECT state FROM cases WHERE id=?", (cid,)).fetchone()["state"] == "AWAITING_APPROVAL":
                set_state(conn, cid, "COLLECTING")
        pending = list(conn.execute("SELECT id, state, params FROM cases WHERE state IN ('DRAFT', 'SOURCING')"))
        for c in pending:
            approved = "panel_size" in json.loads(c["params"])
            if c["state"] == "SOURCING" and not approved:
                append_event(conn, c["id"], "stage.failed", {"stage": "runner", "error": "pre-stage-6 dev run: no plan approval, cannot resume"})
                set_state(conn, c["id"], "FAILED", reason="pre-stage-6 dev run")
                continue
            append_event(conn, c["id"], "case.resumed", {"from_state": c["state"]})
            threading.Thread(target=continue_case if c["state"] == "SOURCING" else run_case, args=(c["id"],), daemon=True).start()
    finally:
        conn.close()


def retry_case(case_id: str) -> None:
    """Continue a stopped case from its last finished stage: phase 2 if the plan was approved, else phase 1."""
    conn = db.connect()
    try:
        params = json.loads(conn.execute("SELECT params FROM cases WHERE id=?", (case_id,)).fetchone()["params"])
    finally:
        conn.close()
    _guarded(case_id, _source_and_draft if "panel_size" in params else _plan)


def run_case(case_id: str) -> None:
    """Phase 1: screen the question and plan. Then wait for the customer to approve the plan and the spend."""
    _guarded(case_id, _plan)


def continue_case(case_id: str) -> None:
    """Phase 2, started by the plan approval: source, screen, rank, enrich and draft outreach."""
    _guarded(case_id, _source_and_draft)


def _plan(conn, case_id: str) -> None:
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    screen = run_stage(conn, case_id, "s1_question_screen",
                       lambda: s1_question_screen.screen(conn, case["question"], case_id)[0])
    if screen["verdict"] == "refuse":
        set_state(conn, case_id, "REFUSED", reason=screen["reason"])
        return
    run_stage(conn, case_id, "s2_decomposer", lambda: s2_decomposer.decompose(conn, screen["effective_question"], case_id)[0])
    set_state(conn, case_id, "PLANNED")
    append_event(conn, case_id, "job.paused", {"reason": "waiting for the customer to approve the plan and the spend"})


def _source_and_draft(conn, case_id: str) -> None:
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    params = json.loads(case["params"])
    window = {k: params[k] for k in ("min_left", "max_left", "min_years")}
    today = date.today()
    stage_rows = {r["stage"]: json.loads(r["result"]) for r in conn.execute(
        "SELECT stage, result FROM stage_results WHERE case_id=? ORDER BY id", (case_id,))}
    question = stage_rows["s1_question_screen"]["effective_question"]
    subs = stage_rows["s2_decomposer"]
    set_state(conn, case_id, "SOURCING")

    client = CrustdataClient(conn, case_id=case_id, credit_cap=config.case_credit_cap(), transport=crustdata_transport)
    limit = config.dev_max_subquestions()
    work = subs if limit is None else subs[:limit]

    competitor_memo: dict[int, tuple[list[str] | None, str | None]] = {}

    def competitors_of(company_id: int):
        """Competitor domains of a target company, fetched once per case. None means the lookup failed."""
        if company_id not in competitor_memo:
            try:
                domains, call_id = company_api.competitors(client, company_id)
                competitor_memo[company_id] = (domains, call_id)
            except Exception as e:
                append_event(conn, case_id, "competitor.lookup_failed", {"company_id": company_id, "error": f"{type(e).__name__}: {e}"})
                competitor_memo[company_id] = (None, None)
        return competitor_memo[company_id]

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
                    conn, client, chosen["company_id"], today, **window, limit=25, query=f"{sq['expertise']}: {sq['text']}")
                comp_domains, comp_call = competitors_of(chosen["company_id"])
                companies.append({"asked": target["name"], "basis": target["basis"], "resolved": True, "chosen": chosen,
                                  "competitor_domains": comp_domains, "competitors_call_id": comp_call,
                                  "alternatives": len(cands) - 1, "pick": pick, "total_matches": meta["total_count"],
                                  "search_call_id": call_id})
                for p in found:
                    if p["person_id"] not in seen:
                        seen.add(p["person_id"])
                        people.append({**p, "company_id": chosen["company_id"]})
            out[str(sq["index"])] = {"companies": companies, "candidates": people}
        return out

    sourced = run_stage(conn, case_id, "s3_sourcer", source_all)

    def screen_all():
        out = {}
        for idx, v in sourced.items():
            by_company = {c["chosen"]["company_id"]: c["competitor_domains"] for c in v["companies"] if c["resolved"]}
            out[idx] = [s4_people_screen.screen(p, today, {**params, "competitor_domains": by_company.get(p["company_id"])})
                        for p in v["candidates"]]
        return out

    screens = run_stage(conn, case_id, "s4_people_screen", screen_all)

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

    panel_size = params.get("panel_size", config.dev_drafts())
    per_sq = panel_size if config.demo_mode() else min(panel_size, config.dev_drafts())
    enrich_n = max(config.enrich_top(), per_sq)

    def enrich_all():
        """Fetch the full profile of the top few per sub-question and re-rank them on role descriptions and skills."""
        out = {}
        for sq in work:
            idx = str(sq["index"])
            first = ranked[idx]["ranked"]
            top, rest = first[:enrich_n], first[enrich_n:]
            try:
                people, enrich_call = people_api.enrich_people(client, [p["profile_url"] for p in top if p["profile_url"]])
            except Exception as e:  # enrichment improves the ranking; without it the first-pass ranking stands
                append_event(conn, case_id, "enrich.skipped", {"subquestion_index": sq["index"], "error": f"{type(e).__name__}: {e}"})
                out[idx] = {**ranked[idx], "enriched_person_ids": [], "enrich_call_id": None, "enrich_skipped": True}
                continue
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

    final = run_stage(conn, case_id, "s5b_enrich_rerank", enrich_all)

    company_names = {str(c["chosen"]["company_id"]): c["chosen"]["name"]
                     for v in sourced.values() for c in v["companies"] if c["resolved"]}
    run_stage(conn, case_id, "s6_outreach_writer", lambda: s6_outreach_writer.write_drafts(
        conn, case_id, work, {idx: r["ranked"] for idx, r in final.items()}, screens, company_names, per_sq))
    set_state(conn, case_id, "AWAITING_APPROVAL")
    append_event(conn, case_id, "job.paused", {"reason": "the invitations are waiting for the customer to approve them"})
