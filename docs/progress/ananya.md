# Ananya: progress log

Append-only. One entry per commit or session, newest at the bottom (template: `docs/TEAM_README.md` section 10).

## 2026-11-22 13:55 IST ananya web-skeleton
Done:
- Next.js app in `web/` (official generator, command below). Typed API client `web/src/lib/api.ts` (customer and operator routes kept apart), live event hook `web/src/lib/useCaseEvents.ts` (reconnects after each `job.paused` with Last-Event-ID).
- Screens: Ask `/` (`web/src/app/page.tsx`); live case page `/cases/[id]` (`web/src/app/cases/[id]/CaseView.tsx`) on `/customer/...` routes only, with plan approval (quote, panel size, budget), stage progress, anonymised panel cards, exclusion reasons by `ref`, outreach counts, simulated ledger, cost counters; approval queue `/operator/approvals` (`web/src/app/operator/approvals/page.tsx`).
- `CLAUDE.md`: web run and check commands filled in.
- Real dev run, case `cc1d86ae311f` (my local DB): ask, plan approval, stages 3 to 6, ended `AWAITING_APPROVAL` with 4 drafts. 10.7 credits, $0.038. Customer view checked: no person name, link, location or email. Drafts not approved (needs a human click; Mailpit was not running).
- Inbox to Dev: `docs/inbox/dev/2026-11-22-ananya-named-company-marked-inferred.md` (company named in the question marked `inferred` and skipped by sourcing) and `...-patch-named-company-first.md` (ready patch, 72 tests pass). Not committed to Dev's files.
In progress: nothing half done. Pages not yet viewed in a real browser (only routes checked).
Next:
1. Expert page `/expert/[token]` and `server/app/routes/expert.py` (uses `expert_context`, accepts only `SENT`), plus `server/app/db/schema_expert.sql` and `server/requirements/expert.txt`.
2. Stage 7 response screen and a coverage meter on the case page.
3. Audit trail and cost log screen; then stage 8 memo.
Decisions:
- Customer screens use only `/customer/...` routes; operator screens (approval queue, audit) use the operator routes.
- The approval queue picks the approver (`ananya` or `dev`) from a dropdown; no login (matches the one-account plan).
- Commits from me will each add an entry here, so Dev can follow every change.
Blocked on: Dev, the large model price in `server/app/core/llm.py` before stage 8 (I will send the model id and price as a request file). Dev, applying the named-company patch before the demo.
Contracts touched: none.

Libraries and tools to credit in the README (rule 7): Next.js 16.4.6, React 19.3.0, Tailwind CSS 4.3.3, TypeScript, ESLint with eslint-config-next (all npm, from create-next-app).
Commands run (rule 10): `npx --yes create-next-app@latest web --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack --disable-git --yes`; `npm install` (inside the generator).

## 2026-11-22 14:04 IST ananya expert-contracts
Done: appended the expert page routes (`GET /expert/{token}`, `POST /expert/{token}/responses`) to `contracts/API.md`, the `response.received` event to `contracts/EVENTS.md`, and response mode, kind and confidence values to `contracts/ENUMS.md`. Additive only.
In progress: the expert page itself (next commit).
Next: see the next entry.
Decisions: `response.received` never carries answer text or personal data, so the customer stream can pass it through.
Blocked on: nothing.
Contracts touched: API.md, EVENTS.md, ENUMS.md (this commit).

## 2026-11-22 14:04 IST ananya expert-page
Done:
- Server: `server/app/routes/expert.py` (expert page API: `GET /expert/{token}` shows persona, sub-questions, simulated payout, only for links whose outreach is `SENT`; `POST /expert/{token}/responses` stores one append-only row per sub-question with a `response_id` the memo can cite, emits `response.received`, moves the case to `COLLECTING`). `server/app/db/schema_expert.sql` (`responses`, append-only triggers). `server/tests/test_expert.py`, 4 tests; full suite 77 pass (with Dev's new decomposer test).
- Web: `/expert/[token]` (`web/src/app/expert/[token]/ExpertView.tsx`): greeting, persona, three ground rules, simulated payout, per sub-question answer / I don't know / can't answer without confidential information, confidence rating, four attestations, one submission per link. `web/src/lib/api.ts`: expert calls and readable validation errors.
- Inbox to Dev: `docs/inbox/dev/2026-11-22-ananya-register-expert-router.md` (two lines for `main.py`).
In progress: nothing half done. Not tried live: needs the router in `main.py` and an approved, sent draft (Mailpit running).
Next:
1. Stage 7 response screen (`server/app/stages/s7_response_screen.py`), run after each submission; `response_screens` table.
2. Coverage meter and screened-answer counts on the case page.
3. Audit trail and cost log screen.
Decisions: one submission per link (answers are never edited). Simulated expert payout `SYNEX_EXPERT_PAYOUT`, default 50, no ledger entry yet.
Blocked on: Dev, two lines in `server/app/main.py` to serve the expert routes (request file above). Dev, large model price before stage 8.
Contracts touched: API.md, EVENTS.md, ENUMS.md in the previous commit.

## 2026-11-22 14:27 IST ananya design-pass
Done: applied the dark design from Ananya's Claude Design mockup ("Synex UI mockups") to the web app.
- Layout: `web/src/app/layout.tsx` (fonts, dark only), `web/src/app/(main)/layout.tsx` (operator/customer shell, honest footer), `web/src/components/Nav.tsx` (Ask, approval queue with pending count, Mailbox link to Mailpit, Audit trail). Pages moved into the `(main)` route group; URLs unchanged. Expert page has its own narrow layout.
- Case page `web/src/app/(main)/cases/[id]/CaseView.tsx`: tabs Plan (plan + approve-and-hold card, then sub-question cards with anonymised panel), Live (panel status board, responses received from `response.received` events with no text, live event stream), Ledger (balance, simulated ledger, per-case cost log from `/cases/{id}/costs`).
- New audit screen `web/src/app/(main)/operator/audit/page.tsx`: `/audit/events` with case and type filters, prev to hash column, Verify chain (`/audit/verify`), Export JSON, cost totals (`/costs`) and per-case cost log. Shared `web/src/components/CostTable.tsx`.
- Expert page `web/src/app/expert/[token]/ExpertView.tsx`: steps landing (rules, payout, attestations) then answers then review (re-confirm) then thank you.
- Checked: lint, types, build; every page 200 against the live server.
In progress: nothing.
Next: stage 7 response screen, then coverage and screened responses on the Live tab.
Decisions: left out mockup parts with no backend or that break rules: memo tab, coverage meter, held responses, payouts, voice interview, decline / never-contact buttons, editable To address, in-browser mailbox (we use Mailpit), "revised answer replaces this one" (answers are append-only), "autosaved", "reset prototype data". They come back as their stages are built.
Blocked on: Dev, expert router in `server/app/main.py` (request in `docs/inbox/dev/`).
Contracts touched: none.

## 2026-11-22 14:38 IST ananya stage7-contracts
Done: stage 7 routes, `response.screened` event and verdict values appended to `contracts/API.md`, `EVENTS.md`, `ENUMS.md`. Additive only.
In progress: stage 7 code (next commits).
Next: see next entries.
Decisions: `response.screened` carries no text or reason. Held answers are reviewed by team members only (not the customer).
Blocked on: nothing.
Contracts touched: API.md, EVENTS.md, ENUMS.md (this commit).

## 2026-11-22 14:38 IST ananya stage7-server
Done: stage 7 response screen. `server/app/stages/s7_response_screen.py` (small model proposes accepted / redacted / held / rejected with exact quotes; code verifies quotes, holds on leak phrases or an unverifiable reply, records dont_know / confidential as rejected without a model call). `response_screens` table in `server/app/db/schema_expert.sql` (append-only). Routes `server/app/routes/responses.py`: customer responses and coverage, operator held list, team-member accept / reject. Screening runs in the background after each submission (`server/app/routes/expert.py`). Tests `server/tests/test_response_screen.py` (7); full suite 90 pass.
In progress: nothing.
Next: web Live tab and operator held queue (next commit); then customer "Review invitations" step; then stage 8.
Decisions: held answers are reviewed by team members only; a review adds a row, never edits text.
Blocked on: Dev, large model price for stage 8.
Contracts touched: previous commit.
