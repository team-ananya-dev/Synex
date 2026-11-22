# Events

Written 2026-11-22 by Dev. Append-only: a change needs a message to the other person first.

Every event is a row in the hash-chained `events` table and is sent live on `GET /cases/{id}/events` (server-sent events). Each message has `id:` (the event id, usable as `Last-Event-ID` or `?after=`), `event:` (the type) and `data:` (JSON). The JSON always has `id`, `type`, `at` (UTC time) and the fields below.

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `case.created` | `question` | A case was created. |
| `case.state` | `state` (see ENUMS.md), `reason` on `REFUSED` | The case changed state. |
| `stage.started` | `stage` | A stage began. |
| `stage.done` | `stage`, `result` | A stage finished. `result` is the stage result (see API.md). |
| `stage.failed` | `stage`, `error` | A stage raised an error. A `case.state` of `FAILED` follows. |
| `crustdata.call` | `call_id`, `endpoint`, `purpose`, `status`, `credits`, `cache_hit` | One Crustdata call and its cost in credits. `call_id` is what memo claims cite. |
| `llm.call` | `call_id`, `purpose`, `model`, `attempt`, `tokens_in`, `tokens_out`, `cost_usd`, `valid` | One model call and its cost. |
| `job.paused` | `reason` | The job reached the end of what is built. The stream closes after this event. |

The stream also closes after a `case.state` of `REFUSED` or `FAILED`. Events carry no secrets. `stage.done` results include candidate details, which are real people's profile data: show them in the app, never put them in the README or a screenshot in the repo.

## Added 2026-11-22

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `competitor.lookup_failed` | `company_id`, `error` | The competitor list for a target company could not be fetched. People from that company are marked `review`. |

## Added 2026-11-22 (stage 6)

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `approval.requested` | `outreach_id`, `person_id`, `persona`, `subquestion_indices`, `flagged` | A draft is waiting in the approval queue. No name or address in the payload. |
| `approval.approved` | `outreach_id`, `by` | A team member clicked approve. |
| `approval.rejected` | `outreach_id`, `by` | A team member clicked reject. |
| `mail.sent` | `outreach_id`, `to` | The email was handed to the mail server (Mailpit in development). |
| `mail.blocked` | `outreach_id`, `reason` | Refused: the address is not on the teammate allowlist. |
| `mail.failed` | `outreach_id`, `error` | The mail server could not be reached or refused the message. |

The stream closes at `job.paused`; events after it (`approval.*`, `mail.*`) need a new connection with `?after=`.

## Added 2026-11-22 (plan approval and ledger)

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `plan.approved` | `panel_size`, `budget`, `hold`, `currency` | The customer approved the plan. Sourcing starts. |
| `ledger.hold` | `amount`, `currency`, `ref`, `by` | Simulated hold placed. |
| `ledger.capture` | `amount`, `currency`, `ref`, `by` | Simulated charge for one answered sub-question (`ref` is `subquestion:<n>`). |
| `ledger.release` | `amount`, `currency`, `ref`, `by` | Unused hold released. |

`job.paused` now also happens at `PLANNED`. The customer stream (`/customer/cases/{id}/events`) removes personal data as described in `API.md`.

## Added 2026-11-22 (Ananya, expert page)

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `response.received` | `response_id`, `subquestion_index`, `kind` (`answer`, `dont_know`, `confidential`), `mode` | An expert answered one sub-question. No answer text and no personal data, so the customer stream can pass it through unchanged. |

## Added 2026-11-22 (customer approval of invitations)

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `outreach.batch_approved` | `sent`, `dropped`, `blocked`, `failed`, `by` | The customer approved the invitations. One event per batch, after the per-email events below. |

`approval.approved` and `approval.rejected` are still emitted once per email, now with `by: "customer"`. The customer stream carries only `outreach_id` for `approval.*`, `mail.sent`, `mail.blocked` and `mail.failed`.

## Added 2026-11-22 (Ananya, stage 7)

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `response.screened` | `response_id`, `subquestion_index`, `verdict`, `by` (`screen` or the team member who reviewed a held answer) | A screening decision. No answer text and no reason, so the customer stream can pass it through unchanged. |
