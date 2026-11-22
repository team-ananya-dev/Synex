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
