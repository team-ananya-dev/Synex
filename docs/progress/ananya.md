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
