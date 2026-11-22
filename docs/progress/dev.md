# Dev progress log

Append only. Template: `docs/TEAM_README.md` section 10.2.

## 2026-11-22 13:26 Dev lead session
Done:
- Server skeleton, hash-chained events, logged Crustdata client with credit cap and dev cache: `server/app/core/`, `server/app/crustdata/`.
- Stages 1 to 6: question screen, decomposer, sourcer (company by id, relevance-ranked search inside hard filters), people screen (rules 1 to 6 and minimum tenure, with a reason each), ranker (evidence checked in code), shortlist enrichment, outreach writer: `server/app/stages/s1_` to `s6_`.
- Case job runner in two phases with a live event stream (operator and customer-safe versions): `server/app/jobs/`.
- Plan approval gate and simulated ledger: `server/app/actions/ledger.py`, `POST /customer/cases/{id}/approve-plan`.
- Approval queue and mail gate (teammate allowlist hard-coded, one send function): `server/app/actions/`.
- Audit trail and cost log endpoints: `server/app/jobs/audit_routes.py`.
- Contracts: `contracts/API.md`, `EVENTS.md`, `ENUMS.md`, `OWNERS.md`. Notes to Ananya in `docs/inbox/ananya/`.
In progress: nothing half done.
Next:
- Wire capture and release into the ledger once responses exist (needs Ananya's response screen).
- Rule 7 (closed period) and the do-not-contact table; restricted list setting.
- Help Ananya connect the expert page to `expert_context` in `server/app/actions/queue.py`.
Decisions:
- No Apollo or ContactOut: the rulebook says agents never contact real people and only permitted APIs are allowed. Outreach goes to a teammate allowlist through Mailpit.
- The customer never sees names, profile links or emails: operator routes and customer routes are separate (`contracts/API.md`).
- The customer approves the plan and the spend before any Crustdata credit is used.
- Price per sub-question is a placeholder (100, simulated): the real rate is undecided.
Blocked on: nothing. Ananya has not pushed yet (checked 13:26).
Contracts touched: all four files in `contracts/`, additive, see commits.

Libraries and tools to credit in the README (rule 7): FastAPI, Uvicorn, httpx, pydantic, pytest, the Anthropic Python SDK (all pip), uv (Astral), Mailpit v1.34.0 (axllent, MIT, from its GitHub release, checksum checked).
Commands run (rule 10): `uv venv .venv`; `uv pip install -r requirements.txt --python .venv/bin/python`; Mailpit downloaded from `github.com/axllent/mailpit/releases` and copied to `~/.local/bin`.
