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
