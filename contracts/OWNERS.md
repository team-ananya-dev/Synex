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
| `SYNEX_DEV_SUBQUESTIONS`, `SYNEX_DEV_COMPANIES`, `SYNEX_DEV_ENRICH` | Development limits (2, 1, 3). Off in demo mode, which uses all sub-questions, 3 companies and 5 enriched people. |
| `SYNEX_DEV_DRAFTS` | Outreach drafts per sub-question (2 while developing, 3 in demo mode). |
| `SYNEX_SMTP_HOST`, `SYNEX_SMTP_PORT` | Mail server (default `localhost:1025`, Mailpit). |
| `SYNEX_EXPERT_BASE_URL` | Base of the private expert link (default `http://localhost:3000`). |
| `SYNEX_PRICE_PER_SUBQUESTION` | Simulated price per answered sub-question (default 100). A placeholder: the real rate is undecided. |

The teammate mail allowlist and the list of registered approvers are hard-coded in `server/app/actions/mail.py` (Dev). Table `outreach` is Dev's.

Tables `ledger` (append-only) and `cases`, `stage_results` are Dev's.
