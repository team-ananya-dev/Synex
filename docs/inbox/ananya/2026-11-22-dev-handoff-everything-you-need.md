# From Dev: everything you need to build your half

Written 2026-11-22. This replaces nothing: the two earlier notes in this folder still apply. Read this one first, then `contracts/API.md` (the part titled "Changes 2026-11-22 (Dev): customer routes, plan approval, ledger, audit and cost log" is the one that matters most), then `contracts/EVENTS.md` and `contracts/ENUMS.md`.

The build guide's schedule says one full case must run by 5:15 into the build, which is about 15:30 today. The backend for stages 1 to 6 is done and tested (71 tests), so you are not waiting on me for anything except the items in section 9.

## 1. Get running (about 10 minutes)

```
git pull                                   # merge, never rebase or force
cp .env.example .env                       # then fill CRUSTDATA_API_KEY and SYNEX_ANTHROPIC_KEY by hand
cd server && uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python
.venv/bin/python -m pytest -q              # 71 pass
SYNEX_DEV_CACHE=1 .venv/bin/uvicorn app.main:app --port 8000     # API docs at http://localhost:8000/docs
mailpit                                    # separate terminal. Install: docs/SETUP_RUNBOOK.md A6. SMTP 1025, inbox http://localhost:8025
```
- Your database is local to your machine (`data/synex.db`, git-ignored). Mine is not shared with you. To see real data, run a case on your machine: it costs about 10 Crustdata credits and 4 cents of model spend with the dev limits.
- Never set `ANTHROPIC_API_KEY`. The server reads `SYNEX_ANTHROPIC_KEY` from `.env`.
- Dev limits are on by default (2 sub-questions, 1 company each, 5 people per search, 3 enriched, 2 drafts per sub-question). `SYNEX_DEMO=1` removes them. `CLAUDE.md` has the commands.
- The CORS setting already allows `http://localhost:3000` for your Next.js app.

## 2. How a case moves (the lifecycle your screens follow)

1. Customer asks: `POST /cases {"question": "..."}`. Job screens the question and plans. State `PLANNED`, event `job.paused`. No Crustdata credit spent yet. A refused question ends `REFUSED`.
2. Customer reads the plan and the quote and clicks approve: `POST /customer/cases/{id}/approve-plan {"panel_size": 1..5, "budget": n}`. A simulated hold is placed. State `SOURCING`.
3. Job sources, screens people, ranks, enriches the shortlist and drafts one email per panel member. State `AWAITING_APPROVAL`, event `job.paused`.
4. An operator (you or me) approves or rejects each draft in the approval queue. Approve sends the email to **Mailpit**, addressed to a teammate (see section 5).
5. **From here on it is your part:** the teammate opens the private link, answers as that persona, the response screen runs, the memo updates live, the case closes, the ledger captures or releases money.

The SSE stream closes at every `job.paused`. After the customer approves the plan, open it again with `?after=<last event id>`.

States you set yourself (call `runner.set_state(conn, case_id, "COLLECTING")` from `server/app/jobs/runner.py`): `COLLECTING` when the first response arrives, `SYNTHESIZING` while a memo is being written, `DELIVERED` when the case closes. I do not set these.

## 3. Screens and the routes they use

| Screen | Audience | Routes |
| --- | --- | --- |
| Ask | customer | `POST /cases` |
| Plan and panel | customer | `GET /customer/cases/{id}` (`plan`, `quote`, `panel`, `screening`), `POST /customer/cases/{id}/approve-plan`, `GET /customer/cases/{id}/events` |
| Live case page | customer | `GET /customer/cases/{id}` and the customer stream. Your response and coverage data comes from your own routes. |
| Memo | customer | yours |
| Audit trail and cost log | customer and admin | `GET /audit/events?case_id=`, `GET /audit/verify`, `GET /cases/{id}/costs`, `GET /costs` |
| Approval queue | operator | `GET /approvals?status=DRAFTED`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject` with `{"approver": "dev"}` or `{"approver": "ananya"}` |
| Expert page | expert (a teammate) | `GET /expert/{token}` and the response routes, yours in `server/app/routes/expert.py` |

**The rule you must not break:** a customer screen never shows a name, a profile link, a headline, a city or an email. If a customer sees them they contact the expert directly and skip us. Customer screens use only `/customer/...` routes. The operator routes (`/cases/{id}`, `/cases/{id}/events`, `/approvals`, `/audit/*`) contain real people's details, so they belong on operator screens only. Experts appear to customers as an anonymised card with an opaque `ref`. Every money amount is simulated: write "simulated" next to it.

Things the customer view already gives you so you do not have to compute them: the quote, the ledger balance and entries, the panel cards (best first, with `fit`, `score`, `reason`, `evidence`, `evidence_hidden`), screening counts and the reason each removed person was removed (by `ref`, no name), the outreach status counts, the cost.

## 4. Data you will want for synthesis

Read stage results server-side with `from app.jobs.views import operator_view`, then `operator_view(conn, case_id)["stages"]`, or query the `stage_results` table (latest row per stage wins). Fields on each candidate (stage `s3_sourcer`, then carried into `s5_ranker` and `s5b_enrich_rerank`): `person_id`, `title`, `function`, `start_date`, `end_date`, `tenure_months`, `company_id`, `country`, `location` (operator only, never display), `current_employers`, `current_roles`, `source_call_id`, `score`, `fit`, `evidence`, `role_description`, `skills`.

- **Independence rule** (context file section 8): two experts with the same company, function and city and at least 3 months overlap count as one source. Compute it from these fields (`company_id`, `function`, `location`, `start_date`, `end_date`), not from who typed the answer. The `function` field is often empty in Crustdata, so fall back to the title.
- **Citations:** every claim needs source ids. Available ids: your own response ids, the Crustdata call id of the search that found a person (`source_call_id`, also the `crustdata.call` events), and the company data call ids (`search_call_id`, `competitors_call_id` in the `s3_sourcer` result). The cite-or-drop checker is yours.
- **Memo labels:** the site flow names experts E1, E2 and so on. Number them yourself from the panel order. If fewer than 3 accepted experts share a role label, coarsen the label.
- **Crustdata cross-check** (optional): company enrich with `headcount` returns `by_role_absolute` (headcount per function) at 2 credits. `server/app/crustdata/client.py` has `CrustdataClient.post(...)`, which logs the call and its cost for you.

## 5. Expert page and response intake (your side)

- Each approved draft is an email to a **teammate address** on the hard-coded allowlist (`server/app/actions/mail.py`: Dev's and yours, alternating). A real expert's address is never stored. The teammate plays the expert. The email body holds a private link `http://localhost:3000/expert/<token>`. Change the base with `SYNEX_EXPERT_BASE_URL`.
- Resolve a token server-side: `from app.actions.queue import expert_context`; `expert_context(conn, token)` returns `None` for an unknown token, else `{"outreach_id", "case_id", "person_id", "first_name", "status", "subquestions": [{"index", "text"}]}`. **Only accept a link whose `status` is `SENT`.** For `DRAFTED`, `REJECTED`, `BLOCKED` or `FAILED` show "not available". It contains no customer information and nothing about other experts.
- Store each response with `case_id`, `person_id`, `outreach_id`, the sub-question `index` and its own id, so the memo can cite it. Put the tables in `server/app/db/schema_expert.sql` (`responses`, `response_screens`, `findings`). Every `schema_*.sql` is loaded automatically at startup. Keep result tables append-only like mine: see the triggers at the top of `schema_core.sql`.
- The expert page must show: the topic in neutral terms, the sub-questions, the payout (simulated), and the three ground rules (nothing confidential, nothing under NDA, nothing non-public about the company's finances). It must **not** name the customer.
- Open question for the help desk (not decided): whether a teammate typing a persona's answer is acceptable. Our reading: counterparties' replies are inputs; the system's results (candidates, screens, memo) are never typed by anyone.

## 6. Shared code you should use (do not copy it)

```python
from app.core import db
from app.core.events import append_event            # audit chain; every event you emit goes here
from app.core import llm
from app.actions import ledger
from app.jobs import runner

conn = db.connect()

# One wrapper for every model call: logs prompt, response, tokens, dollars; one retry; budget guard.
reply, call_id = llm.call_json(
    conn, purpose="screen_response", case_id=case_id,
    system="...", user="...", schema={...JSON schema...},      # the model answers through a forced tool
    validate=lambda r: ...,                                    # raise ValueError to trigger the one retry
    model=llm.SMALL_MODEL,                                     # llm.LARGE_MODEL for the memo only
)

append_event(conn, case_id, "response.received", {"response_id": rid, "subquestion_index": 1})
runner.set_state(conn, case_id, "COLLECTING")

# Money (simulated). Capture only what was earned; release the rest at close.
ledger.capture(conn, case_id, subquestion_index=1, amount=100.0, by="system")   # raises if more than the remaining hold
ledger.release_remaining(conn, case_id, by="system")
```
- **Large model price:** `core/llm.py` has no price for the large model, so a call with it raises on purpose. Send me a request file in `docs/inbox/dev/` with the model id and the price per million tokens from the console, and I will add it. Do not edit `llm.py`.
- Look at `server/app/stages/s5_ranker.py` for a worked example of a stage that makes the model quote evidence and then verifies the quotes in code. The same pattern (never trust the model's claim, check it in code) fits your response screen and the cite-or-drop checker.
- Pricing rule from the product spec: capture only for a sub-question with at least 2 independent accepted responses; a single-source sub-question is charged at a reduced rate or delivered free (the rate is undecided, ask Dev); release the rest. Experts are paid per accepted response (also simulated).
- Event names for your side: add them to `contracts/EVENTS.md` as you create them (suggested: `response.received`, `response.screened`, `memo.updated`, `case.closed`). Customer-facing events must not carry personal data: if you add one with names or text from an expert, tell me and I will add it to the customer stream's redaction in `server/app/jobs/views.py`.

## 7. Rules that bind your parts (rulebook)

- No hard-coded, stored or hand-entered results. No mock shown as live. A person may only approve or reject, or answer as a persona on the expert page. Nobody edits a response, a screen result, the audit trail or the cost log.
- The response screen returns one of: accepted, redacted (flagged span removed), held (waits for a teammate's approve or reject), rejected (excluded, reason logged).
- No code from earlier projects. Credit every library you add in the README, and record any scaffolding command you run (for example the Next.js generator) in `docs/progress/ananya.md`.
- Free voice only (Chrome speech APIs). Claude API budget for the running app is $25 in total and the budget guard in `llm.py` enforces it. Keep about $5 for the finals.
- Commit small and often, format `<area>: <what changed>`, no co-author lines. Run `/sync` before every push.

## 8. Contract points to be aware of

- Everything I added is additive except one behaviour change: `POST /cases` now stops at `PLANNED` and waits for the customer. It is documented in `contracts/API.md`. If you disagree with any contract, message me before building against a different shape.
- Operator routes have no login (the plan is one pre-made account). Do not claim access control anywhere.
- Case ids, `person_id` and call ids are strings or integers exactly as shown in `API.md`. `person_id` is Crustdata's id: never show it to a customer, use `ref`.

## 9. What I have not built, and what I will do next

- Not built: do-not-contact table, rule 7 (closed period), a restricted-list setting, expert payouts (simulated, need an approval click), and setting `COLLECTING` automatically when the first email is sent. Say if you want any of these sooner.
- I can add a demo route or a script on request. I will not enter or edit results.
- Send requests as new files in `docs/inbox/dev/`. Tell me what you have built so far when you push, and which route or field you are missing.
