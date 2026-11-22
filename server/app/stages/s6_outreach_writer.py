"""Stage 6: draft one outreach email per panel member and put it in the approval queue.

The model sees only the role, the company, the tenure and why the person fits, never their name or
anything about the customer. Code fills in the greeting and the private link, and checks the draft:
exactly one link, no other URL, payment labelled simulated, no name leaked.
"""
import re

from .. import question_assignment
from ..actions import mail, queue
from ..core import config, llm

SCHEMA = {
    "type": "object",
    "properties": {"subject": {"type": "string"}, "body": {"type": "string"}},
    "required": ["subject", "body"],
}

SYSTEM = (
    "You write a short, polite outreach email from Synex, a research service, inviting a former employee to answer "
    "a few questions on a private web page. Start with 'Hello {{first_name}},'. Include the questions given, in plain words. "
    "Say clearly: it is voluntary; answers are screened and must not contain confidential or non-public company "
    "information; they are paid per accepted answer, and in this demonstration the payment is simulated; the private link "
    "is {{link}} (write it exactly like that, once). Mention their past role only in general terms. "
    "Plain text only: no markdown, no asterisks, no headings. Say how many questions there are and that each can be answered, skipped with 'I don\'t know', or declined if it would need confidential information. Under 220 words including the questions. Do not mention who the customer is. Do not invent facts. No other links. Sign off as 'The Synex team'."
)


def validate(draft: dict, name: str | None) -> None:
    body, subject = draft["body"], draft["subject"]
    if not subject.strip() or len(subject) > 100:
        raise ValueError("subject must be 1 to 100 characters")
    if body.count("{{link}}") != 1:
        raise ValueError("the body must contain {{link}} exactly once")
    if "{{first_name}}" not in body:
        raise ValueError("the greeting must use {{first_name}}")
    if "**" in body or re.search(r"^\s*#", body, re.M):
        raise ValueError("plain text only: no markdown")
    if re.search(r"https?://|www\.", body):
        raise ValueError("no links other than {{link}}")
    if "simulated" not in body.lower():
        raise ValueError("the body must say the payment is simulated")
    for part in (name or "").split():
        if len(part) > 2 and re.search(rf"\b{re.escape(part)}\b", body, re.I):
            raise ValueError("do not use the person's name; use {{first_name}}")
    if len(body.split()) > 300:
        raise ValueError("keep the email under 220 words, the questions included")


def spread_by_company(panel: list[dict], n: int) -> list[dict]:
    """The n panel members to invite, spread across companies: the best person from each company first (companies
    ordered by their best-ranked person), then a second person from each, and so on. One company cannot fill
    every seat while others were searched, so the customer hears from more than one employer's former staff."""
    queues: dict[object, list[dict]] = {}
    for person in panel:                       # panel is best first, so each queue is too
        queues.setdefault(person.get("company_id"), []).append(person)
    out: list[dict] = []
    while len(out) < n and any(queues.values()):
        for company in list(queues):           # dict order = order of each company's best person
            if queues[company] and len(out) < n:
                out.append(queues[company].pop(0))
    return out


def write_drafts(conn, case_id: str, subs: list[dict], panels: dict[str, list[dict]], screens: dict[str, list[dict]],
                 company_names: dict[str, str], per_subquestion: int) -> list[dict]:
    """panels: sub-question index -> ranked panel. One draft per person, listing every sub-question they were picked for."""
    chosen: dict[int, dict] = {}
    for sq in subs:
        idx = str(sq["index"])
        for person in spread_by_company(panels.get(idx, []), per_subquestion):
            entry = chosen.setdefault(person["person_id"], {"person": person, "subs": []})
            entry["subs"].append(sq)
    question_assignment.assign(conn, case_id, chosen, subs, panels)   # top each expert up to a fixed few questions
    out = []
    for n, (person_id, entry) in enumerate(chosen.items()):
        p, sqs = entry["person"], entry["subs"]
        existing = conn.execute("SELECT id, to_address, flags FROM outreach WHERE case_id=? AND person_id=?",
                                (case_id, person_id)).fetchone()
        if existing:  # drafted before a crash or a retry
            out.append({"outreach_id": existing["id"], "person_id": person_id, "persona": p["title"],
                        "subquestion_indices": [s["index"] for s in sqs], "to_address": existing["to_address"],
                        "flagged": existing["flags"] != "[]"})
            continue
        flags = []
        for idx in {str(s["index"]) for s in sqs}:
            for s in screens.get(idx, []):
                if s["person_id"] == person_id:
                    flags += [{"rule": r["rule"], "reason": r["reason"]} for r in s["results"] if r.get("flag")]
        company = company_names.get(str(p["company_id"]), "their former employer")
        questions = "\n".join(f"- {s['text']}" for s in sqs)
        draft, call_id = llm.call_json(
            conn, purpose="draft_outreach", case_id=case_id, schema=SCHEMA, system=SYSTEM,
            validate=lambda d: validate(d, p["name"]),
            user=f"Former role: {p['title']} at {company}, {p['tenure_months']} months.\nWhy they fit: {p['reason']}\n"
                 f"Questions to ask:\n{questions}",
        )
        to = mail.ALLOWLIST[n % len(mail.ALLOWLIST)]  # persona routing: a teammate plays this expert
        oid = queue.create_draft(
            conn, case_id=case_id, person_id=person_id, name=p["name"], persona_title=p["title"], persona_company=company,
            tenure_months=p["tenure_months"], subquestion_indices=[s["index"] for s in sqs], flags=flags, to_address=to,
            subject=draft["subject"].strip(), body_template=draft["body"], link_base=config.expert_base_url(), llm_call_id=call_id)
        out.append({"outreach_id": oid, "person_id": person_id, "persona": f"{p['title']} ({company})",
                    "subquestion_indices": [s["index"] for s in sqs], "to_address": to, "flagged": bool(flags)})
    return out
