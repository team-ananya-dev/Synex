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

## 2026-11-22 15:25 Dev results session (worktree dev/results)
Done:
- Contract `contracts/2026-11-22-dev-results.md`: result route, summary step, independence rule. Dev takes the s8 result (OWNERS listed s8 under Ananya).
- Stage 8 result `server/app/stages/s8_result.py`, routes `server/app/routes/result.py` (`GET /customer/cases/{id}/result`, `POST .../result/summary`), tests `server/tests/test_result.py`. Two lines in `server/app/main.py`.
In progress: nothing half done.
Next: web Result tab (Ananya) on the contract; s7 idempotency request in `docs/inbox/ananya/`.
Decisions:
- Stage 7 was already built by Ananya; not duplicated. Answers by sub-question use her `/customer/cases/{id}/responses`.
- Independence uses the profile's current city (Crustdata has no per-role city). Missing fields count as a separate source and are listed in `independence_unchecked`.
- consensus or split needs the model's judgement; before the summary is written, 2+ sources show "multiple sources, agreement not assessed". The summary uses the small model.
Blocked on: nothing.
Contracts touched: `contracts/2026-11-22-dev-results.md` (new).
