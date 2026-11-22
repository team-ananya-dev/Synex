# Enums

Written 2026-11-22 by Dev. Append-only: a change needs a message to the other person first.

## Case states (`cases.state`, `case.state` events)

`DRAFT`, `PLANNED`, `SOURCING`, `AWAITING_APPROVAL`, `COLLECTING`, `SYNTHESIZING`, `DELIVERED`, `REFUSED`, `FAILED`.

Today the job runner reaches `PLANNED` and `SOURCING`, plus `REFUSED` and `FAILED`. The others are set by later stages.
`REFUSED` and `FAILED` are final.

## Stage names

`s1_question_screen`, `s2_decomposer`, `s3_sourcer`, `s4_people_screen`, `s5_ranker`. Stage 6 onward are not built yet.

## Verdicts

| Where | Values |
| --- | --- |
| Question screen (`s1`) | `allow`, `refuse`, `rewrite` |
| People screen (`s4`) | `pass`, `review` (manual review flag), `fail` |
| Target company basis (`s2`) | `named` (the question mentions it), `inferred` (the model suggested it) |
| Company pick method (`s3`) | `only_match`, `model` |

## Added 2026-11-22

Stage name `s5b_enrich_rerank` (after `s5_ranker`). Fit labels in ranked items: `strong`, `partial` (`weak` is never on the panel).

## Added 2026-11-22 (stage 6)

Stage name `s6_outreach_writer`. Case state `AWAITING_APPROVAL` is now set by the job runner. Outreach statuses: `DRAFTED`, `SENT`, `REJECTED`, `BLOCKED`, `FAILED`. Approvers: `dev`, `ananya`.

## Added 2026-11-22 (plan approval and ledger)

`PLANNED` is now a waiting state: the job pauses there until the customer approves the plan. Ledger kinds: `HOLD`, `CAPTURE`, `RELEASE`. Ledger currency is always `USD (simulated)`.

## Added 2026-11-22 (Ananya, expert page)

Response `mode`: `form`, `voice`, `text`. Response `kind`: `answer`, `dont_know`, `confidential`. Self-rated `confidence`: `low`, `medium`, `high`. Case state `COLLECTING` is set by the first expert response.

## Added 2026-11-22 (customer approval of invitations)

Approvers: `customer` (approves the invitations of their own case), `dev`, `ananya` (registered team members; there are no operator approval routes any more). `AWAITING_APPROVAL` now means: waiting for the customer to approve the anonymised invitations.
