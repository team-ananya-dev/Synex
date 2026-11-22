# Owners

Written 2026-11-22 by Dev. Append-only: a change needs a message to the other person first (see `CLAUDE.md`). The split follows `docs/TEAM_README.md` section 3.

## Directories and files

| Area | Owner |
| --- | --- |
| `server/app/core/`, `server/app/crustdata/`, `server/app/actions/`, `server/app/jobs/` | Dev |
| `server/app/stages/` s1 to s6 | Dev |
| `server/app/db/schema_core.sql`, `server/requirements/core.txt`, `server/tests/` for Dev modules, `server/scripts/` | Dev |
| `web/`, `web/package.json` and lockfile | Ananya |
| `server/app/stages/` s7, s8, `server/app/interview/`, `server/app/routes/expert.py` | Ananya |
| `server/app/db/schema_expert.sql`, `server/requirements/expert.txt` | Ananya |
| `contracts/` | shared, append-only |

## Tables

| Table | Owner | Notes |
| --- | --- | --- |
| `events` | Dev | append-only, hash-chained (triggers block UPDATE and DELETE) |
| `crustdata_calls` | Dev | append-only; one row per Crustdata call, with credits |
| `llm_calls` | Dev | append-only cost log for model calls |
| `dev_cache` | Dev | development only; never read when `SYNEX_DEMO=1` |
| `cases`, `subquestions`, `candidates`, `screen_results`, `outreach`, `ledger` | Dev | added with the stages |
| `responses`, `response_screens`, `findings` | Ananya | `schema_expert.sql` |

## Environment flags

| Variable | Meaning |
| --- | --- |
| `SYNEX_DEMO=1` | Demo and finals mode: the dev cache is never read or written, and the dev result limit is off. |
| `SYNEX_DEV_CACHE=1` | Cache real Crustdata responses in the local DB. Ignored when `SYNEX_DEMO=1`. |
| `SYNEX_DEV_LIMIT` | Maximum results per Crustdata search when not in demo mode. Default 5. |
