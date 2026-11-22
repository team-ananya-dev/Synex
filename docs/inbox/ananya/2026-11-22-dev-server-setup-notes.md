# From Dev: what is on main before you push

Read this before your first push. Nothing here needs a reply unless you disagree.

1. Pull first with `git pull` (merge, no rebase, no force). Main has the `server/` skeleton, `contracts/OWNERS.md`, `.env.example`, and `.gitignore` now ignores `data/`.
2. Requirements: `server/requirements.txt` only includes `requirements/core.txt`. Create your own `server/requirements/expert.txt` and add the line `-r requirements/expert.txt`. Do not edit `core.txt`.
3. Schema: every `server/app/db/schema_*.sql` is loaded automatically at startup, so `schema_expert.sql` needs no wiring.
4. Use the shared plumbing for stages 7 and 8:
   - model calls: `app.core.llm.call_json(...)`. It logs every call to `llm_calls`, retries once on a bad reply and stops at the budget.
   - audit events: `app.core.events.append_event(...)`.
   The large model has no price in `llm.py`. I own that file, so send a request file to `docs/inbox/dev/` with the model id and the price from the console.
5. Environment: `.env` needs `CRUSTDATA_API_KEY` and `SYNEX_ANTHROPIC_KEY`. Never set `ANTHROPIC_API_KEY`. `SYNEX_DEMO=1` turns off the dev cache and the dev result limit.
6. Server setup: `cd server && uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python`, then `.venv/bin/python -m pytest`.
7. Coming from me next, in `contracts/`: `API.md`, `EVENTS.md`, `ENUMS.md` for the case job runner (create a case, read a case, live event stream). Build the web client against those once they are on main.
8. `CLAUDE.md` still says `Commands: TBD`. Whoever settles the run commands first fills them in.
