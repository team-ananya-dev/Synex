# API

Written 2026-11-22 by Dev. Append-only: a change needs a message to the other person first. Server: `cd server && .venv/bin/uvicorn app.main:app --port 8000`. CORS allows `http://localhost:3000`.

## `POST /cases`
Body `{"question": "<5 to 2000 characters>"}`. Returns `201 {"id": "<case id>", "state": "DRAFT"}` straight away. The job runs in the background; follow it with the event stream.

## `GET /cases`
The latest 50 cases: `[{"id", "question", "state", "created_at"}]`.

## `GET /cases/{id}`
```
{
  "id", "question", "state", "refusal_reason", "created_at",
  "stages": { "<stage name>": <stage result> },
  "cost": {"crustdata_credits": 3.3, "model_usd": 0.0173, "credit_cap": 25.0}
}
```
`stages` only has the stages that finished. `404` for an unknown id.

## `GET /cases/{id}/events?after=<event id>`
Server-sent events, see `EVENTS.md`. Replays everything after `after` (default 0, or the `Last-Event-ID` header), then follows live.

## Stage results
Sub-questions are keyed by their `index` (a string, "1", "2", ...) in the per-sub-question stages.

- `s1_question_screen`: `{"verdict", "reason", "effective_question"}`. A rewrite changes `effective_question`.
- `s2_decomposer`: a list of `{"index", "text", "expertise", "title_keywords": [str], "target_companies": [{"name", "basis"}]}`.
- `s3_sourcer`: `{"<index>": {"companies": [...], "candidates": [...]}}`.
  - a company: `{"asked", "basis", "resolved": bool, "chosen": {"company_id", "name", "domain", "year_founded", "size", "industries", "description", "confidence"}, "alternatives": int, "pick": {"method", "confident", "reason", "llm_call_id"}, "total_matches": int, "search_call_id"}`. An unresolved company has only `asked`, `basis`, `resolved: false`.
  - a candidate: `{"person_id", "name", "headline", "location", "profile_url", "title", "function", "start_date", "end_date", "tenure_months", "still_at_company", "current_employers": [str], "record_updated_at", "source_call_id", "company_id"}`. Dates are `YYYY-MM-DD`, to the month. `source_call_id` links to the `crustdata.call` event.
- `s4_people_screen`: `{"<index>": [{"person_id", "verdict", "results": [{"rule", "passed", "reason", "flag"?}]}]}`. Show `reason` to the customer for a failed person.
- `s5_ranker`: `{"<index>": {"ranked": [<candidate fields> + "score" (0 to 100), "reason", "verdict"], "llm_call_id"}}`, best first. Only `pass` and `review` people are ranked.

## Development limits
Unless `SYNEX_DEMO=1`, a case sources only the first 2 sub-questions and 1 company each, and a search returns at most 5 people. These limits exist to save credits and are off in demo mode.

## Changes 2026-11-22 (Dev): relevance ranking and shortlist enrichment
Additive: nothing above was removed.

- `s3_sourcer`: each candidate also has `crustdata_fit` (`strong`, `moderate` or null), Crustdata's own relevance tier. The search now ranks by relevance inside the hard filters, and people who still list the company as a current employer are excluded in the query.
- `s5_ranker` (first pass) per sub-question is now `{"ranked": [...], "excluded": [...], "llm_call_id"}`. Each ranked item has the candidate fields plus `score` (0 to 100), `fit` (`strong` 70+, `partial` 40 to 69), `evidence` (exact snippets from the person's title, headline, function, role description or skills, verified in code), `evidence_dropped` (how many snippets the model gave that could not be verified), `reason`, `data_conflict` (empty, or a note when facts contradict each other, such as a headline that does not fit the job title) and `verdict`. People below 40, or with no verified evidence, are in `excluded` as `{"person_id", "name", "score", "title", "why"}` and are not on the panel.
- New stage `s5b_enrich_rerank`: `{"<index>": {"ranked": [...], "excluded": [...], "enriched_person_ids": [int], "enrich_call_id", "llm_call_id"}}`. The top few per sub-question get their full profile (1 credit each) and are re-scored with `role_description` and `skills` added to their fields. `ranked` here is the final panel order, best first. Use this stage's `ranked` for the plan and panel screen when it exists, else `s5_ranker`.
- Development limits: `SYNEX_DEV_ENRICH` (default 3, 5 in demo mode) sets how many people per sub-question are enriched.

## Changes 2026-11-22 (Dev): rule 4, competitor conflict
Additive: nothing above was removed.

- `s3_sourcer`: each resolved company also has `competitor_domains` (list of website domains, or `null` if the lookup failed) and `competitors_call_id`. Each candidate also has `current_roles`: `[{"company_id", "name", "website", "title", "seniority"}]`.
- `s4_people_screen`: a new rule `rule_competitor` appears in each person's `results`. It fails on a sensitive current role at a direct competitor (seniority Experienced Manager, Director, Vice President, CXO or Owner / Partner, or a strategy, pricing, product, category, procurement, finance or head-type title). Any other role at a competitor gives verdict `review` with a `flag: true` entry. If the competitor list could not be fetched, every person is `review`, never a silent `pass`. Show the `reason` of flagged entries to the operator.

## Changes 2026-11-22 (Dev): stage 6 outreach drafts and the approval queue
Additive: nothing above was removed. Everything here is **operator-only**: it shows real people's names. Never render it on a customer screen.

- A finished job now ends in state `AWAITING_APPROVAL` (after `PLANNED`, `SOURCING`) and emits `job.paused`. The event stream closes at `job.paused`. To follow approvals live, open it again with `?after=<last event id>`: it stays open, so close it client-side.
- Stage `s6_outreach_writer` result: a list of `{"outreach_id", "person_id", "persona", "subquestion_indices", "to_address", "flagged"}`. One draft per person, listing every sub-question they were picked for. `to_address` is always a teammate (see below).
- Persona routing: a real expert's email is never stored. Each draft is addressed to one of the two allowlisted teammate addresses, who plays that expert. The private link in the body is `<SYNEX_EXPERT_BASE_URL>/expert/<token>` (default `http://localhost:3000/expert/<token>`). The expert page route that resolves the token is Ananya's: `server/app/routes/expert.py`. The `token` column of the `outreach` table is the lookup key.

### `GET /approvals?status=DRAFTED&case_id=<id>`
Both filters optional. Returns a list of
`{"id", "case_id", "person_id", "name", "persona_title", "persona_company", "tenure_months", "subquestion_indices", "flags": [{"rule", "reason"}], "to_address", "subject", "body", "status", "decided_by", "decided_at", "sent_at", "block_reason", "llm_call_id", "created_at"}`.
`flags` are the manual-review reasons from the people screen (for example a role at a competitor) that the approver must read. `status` is one of `DRAFTED`, `SENT`, `REJECTED`, `BLOCKED`, `FAILED`.

### `POST /approvals/{id}/approve` and `POST /approvals/{id}/reject`
Body `{"approver": "dev"}` or `{"approver": "ananya"}` (case-insensitive). This is the human click. Returns the updated item.
- `403` if the approver is not a registered team member, `404` for an unknown id, `409` if the draft was already decided.
- Approve sends through the allowlist gate: `SENT` on success; `BLOCKED` (with `block_reason`) if the address is not on the teammate allowlist, which is a visible refusal and an audit event; `FAILED` if the mail server could not be reached. Show `block_reason` to the operator.
- Nothing is sent without this click, and nothing is retried silently.

## Changes 2026-11-22 (Dev): customer routes, plan approval, ledger, audit and cost log
Read this section first: it changes the case lifecycle and says which routes a customer screen may use.

### Operator routes vs customer routes
- **Operator routes** show real people's names, profile links and addresses: `GET /cases/{id}`, `GET /cases/{id}/events`, `GET /approvals`, `GET /audit/*`. Use them only on operator screens (approval queue, audit trail, admin). Never on a customer screen.
- **Customer routes** never contain a name, headline, profile URL, city or email: `GET /customer/cases`, `GET /customer/cases/{id}`, `GET /customer/cases/{id}/events`, `POST /customer/cases/{id}/approve-plan`. The customer screens use only these. `POST /cases` (ask a question) is shared.
- Experts appear to the customer only as an anonymised card with an opaque `ref` (for example `E3fa91c20`), stable inside one case.

### New lifecycle (replaces the "runs straight through" behaviour)
1. `POST /cases` -> the job screens the question and plans (stages 1 and 2), sets state `PLANNED` and emits `job.paused` ("waiting for the customer to approve the plan and the spend"). **No Crustdata credit has been spent.** A refused question ends as `REFUSED`.
2. The customer reads the plan and the `quote`, then `POST /customer/cases/{id}/approve-plan`. This places the simulated hold and starts sourcing.
3. The job runs stages 3 to 6, goes `SOURCING` then `AWAITING_APPROVAL`, and emits `job.paused` ("outreach drafts are waiting for approval").
4. Team members approve drafts (`/approvals`). Later stages (collecting, synthesis) are not built yet.

The event stream closes at every `job.paused`. After approving the plan, open the stream again with `?after=<last event id>`.

### `GET /customer/cases/{id}`
```
{
  "id", "question", "state", "refusal_reason", "created_at",
  "plan": [{"index", "text", "expertise", "title_keywords", "target_companies": [{"name", "basis"}]}] | null,
  "quote": {"subquestions", "price_per_subquestion", "hold_amount", "currency": "USD (simulated)"} | null,   // only while PLANNED
  "approval": {"panel_size", "budget", "hold"} | null,
  "screening": {"<index>": {"considered", "pass", "review", "fail", "excluded": [{"ref", "reasons": [str]}]}},
  "panel": {"<index>": [{"ref", "role", "company", "tenure_months", "left_year", "country", "fit", "score", "reason", "evidence": [str], "evidence_hidden": int}]},
  "outreach": {"DRAFTED": n, "SENT": n, "REJECTED": n, ...},
  "ledger": {"balance": {"held", "captured", "released", "remaining", "currency"}, "entries": [{"kind", "amount", "currency", "ref", "note", "created_by", "created_at"}]},
  "cost": {"crustdata_credits", "model_usd", "credit_cap"}
}
```
`screening.excluded` is how the customer sees that a person was removed and why (no name). `panel` is best first and only holds people who passed the rules and the relevance cut-off. `evidence_hidden` counts evidence snippets that came from the person's self-written headline: they are left out of the card because a headline is easy to search for, so the UI may say "n more signals from the profile summary". `country` comes from the profile's structured location. Every money amount is simulated and says so in `currency`; show "simulated" next to it.

### `POST /customer/cases/{id}/approve-plan`
Body `{"panel_size": 1 to 5, "budget": number}`. `panel_size` is experts contacted per sub-question. Returns `{"id", "state": "PLANNED", "hold": <quote>}`.
`404` unknown case, `409` if the case is not `PLANNED` (already approved, refused, failed), `422` if `budget` is below `quote.hold_amount` (the message names the amount) or `panel_size` is out of range.
In development only the first 2 sub-questions are sourced, so the quote covers 2; with `SYNEX_DEMO=1` it covers all of them.

### `GET /customer/cases/{id}/events`
The same events as the operator stream with personal data removed: `stage.done` results are replaced by customer-safe summaries (`s3_sourcer`: companies and a count; `s4_people_screen`: counts; `s5_ranker` and `s5b_enrich_rerank`: `{"panel": [cards], "left_off": n}`; `s6_outreach_writer`: `{"drafts": n}`), `approval.requested` carries a `ref`, `mail.sent` carries no address.

### Audit trail and cost log (operator)
- `GET /audit/events?case_id=&after=&limit=` -> `[{"id", "case_id", "type", "payload", "at", "prev_hash", "hash"}]`, oldest first.
- `GET /audit/verify` -> `{"ok", "first_bad_event_id", "events_checked"}`. Recomputes the whole hash chain; `ok: false` names the first changed event.
- `GET /cases/{id}/costs` -> `{"crustdata_calls": [...], "llm_calls": [...], "totals": {"crustdata_credits", "model_usd"}}` with call ids, purpose, credits or tokens and dollars. Prompts and responses are not included.
- `GET /costs` -> totals across all cases and the remaining model budget (`model_budget_usd`, `model_remaining_usd`).

### Expert page hand-off (for `server/app/routes/expert.py`)
`from app.actions.queue import expert_context`; `expert_context(conn, token)` returns `None` for an unknown token, else `{"outreach_id", "case_id", "person_id", "first_name", "status", "subquestions": [{"index", "text"}]}`. Only accept a link whose `status` is `SENT`. It holds no customer information and nothing about other experts. Store responses with `case_id`, `person_id`, `outreach_id` and the sub-question index so the memo can cite them.

## Changes 2026-11-22 (Ananya): expert page
Additive. Router `server/app/routes/expert.py` (Ananya); it is served once `main.py` includes it (request to Dev in `docs/inbox/dev/`). These routes are for the expert page only: no customer, no other experts, no contact details.

### `GET /expert/{token}`
`404` for an unknown token. A link whose outreach is not `SENT` returns `{"available": false, "reason"}`. Otherwise:
`{"available": true, "first_name", "persona": {"role", "company", "tenure_months"}, "subquestions": [{"index", "text"}], "submitted": bool, "payout": {"per_accepted_answer", "currency": "USD (simulated)"}}`.

### `POST /expert/{token}/responses`
Body `{"mode": "form" | "voice" | "text", "attestations": {"not_current_employee", "left_as_shown", "no_blocking_confidentiality", "no_confidential_info"}: all true, "answers": [{"index", "kind": "answer" | "dont_know" | "confidential", "text", "confidence": "low" | "medium" | "high" | null}]}`.
Each sub-question of the link exactly once; `text` and `confidence` are required for `kind = answer` and cleared otherwise. Returns `201 {"received": [{"response_id", "subquestion_index", "kind"}]}`.
`404` unknown token, `409` link not `SENT` or already submitted (one submission per link), `422` a statement not confirmed, a sub-question missing or extra, or an empty answer.
Rows go to the append-only `responses` table (`server/app/db/schema_expert.sql`). `response_id` (for example `R3fa91c20`) is what memo claims cite. The first response moves the case from `AWAITING_APPROVAL` to `COLLECTING`.

## Changes 2026-11-22 (Dev): the customer approves the invitations, operators no longer approve emails
Decision record: `contracts/decisions/2026-11-22-dev-customer-approves-invitations.md`.

- **Removed:** `POST /approvals/{id}/approve` and `POST /approvals/{id}/reject`. Nobody sits and approves each email. `GET /approvals` stays, read-only, as the operator's list of every invitation and what happened to it.
- **New lifecycle step 4:** at `AWAITING_APPROVAL` the customer reviews the anonymised invitations (`invites` below) and clicks approve. Listed experts are invited, every other waiting invitation is dropped, and the case moves to `COLLECTING`. Experts who have a `SENT` invitation can then open their private link (your expert page needs nothing else).
- `GET /customer/cases/{id}` has a new field `invites`:
  `[{"ref", "role", "company", "tenure_months", "subquestion_indices", "subject", "preview", "status", "flagged", "flag_reasons": [str], "selected_by_default"}]`.
  `preview` is the email text with the first name and the private link replaced by `[first name]` and `[private link]`. There is no address, name or link anywhere in it. `flagged` experts (a review flag from the people screen, such as a role at a competitor) have `selected_by_default: false` and `flag_reasons` the customer must read: the customer approves or drops them. `status` is `DRAFTED`, `SENT`, `REJECTED`, `BLOCKED` or `FAILED`.
- `POST /customer/cases/{id}/approve-outreach`, body `{"refs": ["E3fa91c20", ...]}` (at least one `ref` from `invites`). Returns `{"sent", "dropped", "blocked", "failed", "state"}` where `state` is `COLLECTING` if at least one email went out, else still `AWAITING_APPROVAL`. `409` if the case is not `AWAITING_APPROVAL` (also on a second click), `422` for an empty list or a `ref` that is not waiting, `404` for an unknown case.
- Mail still leaves only through the teammate allowlist gate. In this competition every invitation goes to a teammate's inbox (Mailpit); `blocked` counts any address the gate refused and `failed` a mail server error (the invitation then shows `FAILED` with the reason in the operator list).
- Customer screens must say what happens to the invitations honestly: they are the anonymised text of what the expert receives. Do not show the real recipient.

## Changes 2026-11-22 (Ananya): stage 7 response screen
Additive. Code: `server/app/stages/s7_response_screen.py`, routes in `server/app/routes/responses.py` (mounted through the expert router). Each submitted answer is screened in the background right after `POST /expert/{token}/responses`.

- Verdicts (latest row per `response_id` in the append-only `response_screens` table): `accepted`, `redacted` (flagged spans replaced by `[redacted]`; the spans are exact quotes, verified in code), `held` (a team member decides), `rejected`. A leak phrase found by the code rule turns a model `accepted` into `held`; an unverifiable model reply is `held`, never `accepted`. `dont_know` and `confidential` answers are `rejected` with that reason and no model call.

### `GET /customer/cases/{id}/responses` (customer-safe)
`{"coverage": {"<index>": {"received", "pending", "accepted", "redacted", "held", "rejected"}}, "responses": [{"response_id", "ref", "role", "company", "subquestion_index", "verdict": "accepted" | "redacted", "text", "confidence", "mode", "created_at"}]}`. Only accepted answers, and redacted ones with the spans removed. `ref` is `views.expert_ref`. No name, link, address or person id. `404` unknown case.

### `GET /operator/responses?status=&case_id=` (operator only)
Every response with its latest screen: `{"response_id", "case_id", "ref", "persona_title", "persona_company", "subquestion_index", "kind", "text", "confidence", "mode", "verdict" (or "pending"), "reason", "redacted_text", "flagged_spans", "code_flags", "decided_by", "llm_call_id", "created_at"}`. Full answer text: never on a customer screen.

### `POST /operator/responses/{response_id}/decide`
Body `{"approver": "dev" | "ananya", "decision": "accept" | "reject"}`. Only for a response whose latest verdict is `held`; adds a new screen row (`accepted` or `rejected`, `decided_by` the team member). The text is never changed. `403` not a team member (the customer cannot review), `404` unknown response, `409` not held, `422` bad decision.

## Changes 2026-11-22 (Dev): payments removed from scope
Decided by the team at about 14:45: no payment provider, no simulated ledger, no payment-like action anywhere.

- `POST /customer/cases/{id}/approve-plan` body is now `{"panel_size": 1 to 5}`. No budget, no hold. Returns `{"id", "state", "quote"}`.
- `quote` (in `GET /customer/cases/{id}`, shown at every state once a plan exists) is `{"subquestions", "price_per_subquestion_inr", "quoted_price_inr", "label": "quoted price, no payment taken"}`. A display figure only. `SYNEX_PRICE_PER_SUBQUESTION_INR` sets the rate (default 8000).
- Removed from the customer view: `ledger`. `approval` is now `{"panel_size"}`.
- `plan.approved` event carries `panel_size`, `quoted_price_inr`, `label`. No `ledger.*` events are emitted any more.
- Expert page payout (Ananya's route) carries `terms: "payout terms shown for illustration; no payment is made in this build"`.
- `cost.credit_cap` comes from `SYNEX_CASE_CREDIT_CAP` (default 25 while developing, 250 in demo mode).

## Changes 2026-11-22 (Ananya): gaps found in the first full run
Additive except where marked. Dev was told in `docs/inbox/dev/2026-11-22-ananya-gap-fixes.md`.

- **Stage 1 (`s1_question_screen`) result** has two new fields: `named_companies` (companies the question names, kept only if the name really appears in the question) and `restored_companies` (names a rewrite dropped and code appended back to `effective_question`). The prompt now says naming a company is not a reason to refuse or rewrite.
- **Coarse role labels (customer-safe).** In `GET /customer/cases/{id}/responses` and `GET /customer/cases/{id}/result`, an answer's `role` is the exact title only when at least 3 different experts with that title have accepted answers in the case; otherwise it is a coarse label such as "Sales manager" or "Senior supply chain leader" (`server/app/anonymity.py`). Panel cards and invitations are unchanged.
- **Changed: `status` in the result** can also be `"not sourced"`: the sub-question was never searched (development limits). `"no accepted answer"` now means it was searched and has nothing accepted yet.
- **Changed: `label` in the result** can also be `"multiple sources, different aspects"` (`label_basis: "model"`): the summary step found that the answers talk about different things. `consensus` and `split` now need the same point to be supported or contradicted.
- **New: `POST /customer/cases/{id}/close`.** The customer ends collection. `200 {"id", "state": "DELIVERED", "answered_subquestions": [int]}`; `409` if the case is not `COLLECTING` or has no accepted answer; `404` unknown case. Emits `case.state` with `state: "DELIVERED"`, `answered_subquestions`, `by: "customer"`. Afterwards expert links that have not submitted show "closed", and `POST /expert/{token}/responses` returns `409`.
- **`GET /expert/{token}`** has a new field `screening` once answers are submitted: `[{"index", "kind", "verdict": accepted|redacted|held|rejected|pending, "reason", "removed": [str]}]`, the expert's own result per answer (site flow: the expert is told which and why).

## Changes 2026-11-22 (Dev): exactly-once sends and resume after a restart
- Outreach status `APPROVED` is new: the customer's click marks every chosen invitation `APPROVED` (and the rest `REJECTED`) before any email is sent, then each goes `SENT`, `BLOCKED` or `FAILED`. A restart finishes every `APPROVED` invitation.
- Table `actions` (Dev): one row per side effect, `key = sha256(case_id|action_type|target_id)`, `PENDING` before the SMTP call, `DONE` after. The key is the email's `Message-ID` (`<key@synex.local>`). A `DONE` action is never repeated; a `PENDING` one found after a crash is checked against the mailbox and sent only if absent; if the mailbox cannot be read it is marked `FAILED` ("not sent again"), never re-sent blind.
- On startup the server continues every case in `DRAFT` or `SOURCING` from its last finished stage (event `case.resumed`). A `SOURCING` case with no plan approval is marked `FAILED` ("pre-stage-6 dev run").
- `server/scripts/kill_test.sh`: live kill -9 in the middle of sending, restart, and a check that the mailbox holds exactly one email per approved invitation.

## Changes 2026-11-22 (Dev): sources on every rule, and CANNOT_VERIFY
- Every people-screen rule result now carries `field_path` (the Crustdata person-record field it read, for example `experience.employment_details.past[2].end_date`), `value`, `record_date` (Crustdata's `metadata.updated_at` for that person) and `source_call_id` (the search call that returned the record).
- New people-screen verdict `cannot_verify`: a field a rule needs is missing (exit or start date). The rule's `passed` is `null`, it has `cannot_verify: true`, and its `reason` names the missing field. Such a person is never ranked or contacted. The customer view's `screening` counts `cannot_verify` and lists the reasons under `excluded`.
- A company name the model cannot resolve with confidence (a lookalike or ambiguous name), or one Crustdata does not know, is not sourced: the `s3_sourcer` company entry is `{"resolved": false, "cannot_verify": true, "reason", "candidates": [{"company_id", "name", "domain", "size"}]}`.
- Candidates carry `role_path` and each `current_roles` item a `path`, the positions in the Crustdata record.

## Changes 2026-11-22 (Ananya): several questions per expert
Additive. Each invited expert now gets a fixed small number of questions (default 3), not only the one they were picked for. Nothing in a route changes: `invites[].subquestion_indices`, `GET /approvals`, `GET /expert/{token}` (`subquestions`) and `POST /expert/{token}/responses` already took a list, and the expert must still answer or skip (I don't know / can't answer without confidential information) each one. The first index is the question the expert was picked for. New event `questions.assigned` in `EVENTS.md`; setting `SYNEX_QUESTIONS_PER_EXPERT` in `OWNERS.md`. The invitation email word limit is now 300 words (it has to carry the questions).

## Changes 2026-11-22 (Ananya): client report (PDF)
Additive. Customer-safe: built from the same screened data as the result screen, with experts only as anonymous refs (never a name, link, city or email). Code: `server/app/report/` (mounted on the expert router, so `main.py` is unchanged).

### `POST /customer/cases/{id}/report/prepare`
Makes the written parts exist for the current accepted answers: the per-sub-question summary (`POST .../result/summary`, if missing or stale) and the executive overview (one small-model call, `purpose: report_overview`, cite-or-drop: a headline or finding that cites no answer of this case is removed). Safe to repeat: the same answers and summaries make no new model call. Returns `200 {"case_id", "summary": "written"|"unavailable", "overview": "written"|"unavailable", "overview_error": null|"<ErrorName>", "ready": true}`. A model failure does not fail the request. `409` no accepted answer yet, `404` unknown case.

### `GET /customer/cases/{id}/report.pdf`
`application/pdf`, `Content-Disposition: attachment; filename="synex-report-<id>.pdf"`. Built from the case's current data, using the stored overview only if it was written for exactly the current answers (otherwise the report says a written overview was not available). `409` until one answer is accepted, `404` unknown case. Sections: cover, executive summary, findings by sub-question, appendices A to E (method, experts who answered, people screening, audit trail and cost, limitations).

New events (`EVENTS.md`): `report.overview_written` `{"llm_call_id", "findings", "dropped_uncited"}` and `report.generated` `{"bytes", "with_overview", "summary_status", "answers_used"}`. Overview is stored append-only in `stage_results` as `s9_report_overview`, keyed on the answers and summaries it used.
