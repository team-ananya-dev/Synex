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
