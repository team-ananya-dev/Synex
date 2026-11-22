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

## 2026-11-22 14:38 IST ananya stage7-web
Done: Live tab coverage (accepted answers against a target of 2 per sub-question) and screened answers with anonymous refs (`web/src/app/(main)/cases/[id]/CaseView.tsx`). Operator page `web/src/app/(main)/operator/approvals/page.tsx` is now "Operator queue": held answers with Accept / Reject, plus a read-only invitation log (Dev removed the per-email approve and reject routes). Nav badge counts held answers. Fixed: the live stream did not listen for `response.*` events.
In progress: nothing.
Next: customer "Review invitations" step; stage 8.
Decisions: none new.
Blocked on: nothing.
Contracts touched: none.

## 2026-11-22 14:41 IST ananya landing-page
Done: landing page at `/` (`web/src/app/page.tsx`), visual style inspired by krillion.io (deep-sea palette, VT323 pixel display font, "descending" depth motif; colours only, no assets copied). Content is Synex's own: hero, data strip, the eight stages as depths, compliance rules and cards, expert-network comparison, "what's real, what's simulated", final call to action. The Ask screen moved from `/` to `/ask` (`web/src/app/(main)/ask/page.tsx`); nav updated. Palette and keyframes in `web/src/app/globals.css`.
In progress: nothing.
Next: customer "Review invitations" step; stage 8 memo.
Decisions: the landing page names only what the code does. Depth 08 (memo) and the hero's "one memo" describe stage 8, which is not built yet: build it or soften those lines before the demo.
Blocked on: nothing.
Contracts touched: none.

Libraries and tools to credit in the README (rule 7), added: VT323 font (Google Fonts, SIL Open Font License), loaded with next/font. Design inspiration: krillion.io (look only).

## 2026-11-22 14:52 IST ananya landing-dive
Done: rebuilt the landing page as an interactive dive (`web/src/components/landing/Landing.tsx`, `sprites.tsx`, `Toys.tsx`; `web/src/app/page.tsx`). Scrolling descends through the eight stages: HUD with depth meter, stage squares and compliance "gates", a depth ruler with a YOU marker, water darkening with depth, light rays near the surface, fish schools, kelp, rising bubbles, a krill that follows the pointer, bubble bursts on click, a menu drawer, real ocean depth facts in the margin, a creature reveal and DESCEND button per stage. Two live toys run the server's own rules in the browser: the people-screen thresholds (sliders) and the stage 7 leak-phrase rule (type an answer). Hero DIVE button sends the question to `/ask?q=`, which now prefills it. All pixel art is original.
In progress: nothing.
Next: customer "Review invitations" step; stage 8 memo.
Decisions: the toys copy thresholds and the regex from the server; if `s4_people_screen.py` defaults or `RISK` in `s7_response_screen.py` change, update `web/src/components/landing/Toys.tsx`. Stage 8 card (memo) still describes unbuilt work.
Blocked on: nothing.
Contracts touched: none.

## 2026-11-22 15:00 IST ananya landing-koi-pond
Done: replaced the Krillion-style dive with an original koi pond (Ananya: too close to Krillion). `web/src/components/landing/Pond.tsx` draws a pixel pond on one canvas at 1/4 resolution: a wave simulation where the pointer leaves a wake and clicks drop stones; koi with chain bodies that wander, leave wakes and flee the pointer and splashes; lily pads, flowers and duckweed pushed by the pointer and by ripples; reeds that bend away; dragonflies that dart off. `Landing.tsx` sits on top (hero "Drop one question. Watch it ripple out to a whole panel.", eight stages, the two rule toys, why Synex, what's real); buttons and cards drop ripples. Font changed to Pixelify Sans. Removed the krill, HUD, depth ruler, sprites and VT323.
In progress: nothing.
Next: customer "Review invitations" step; stage 8 memo.
Decisions: pond art is drawn in code (inspired by a reference image, nothing copied). Memo stage card still describes unbuilt work.
Blocked on: nothing.
Contracts touched: none.

Libraries and tools to credit in the README (rule 7), changed: Pixelify Sans font (Google Fonts, SIL Open Font License) replaces VT323.

## 2026-11-22 15:04 IST ananya landing-calmer
Done: calmer pond after Ananya's review (too fast, too smooth, too hectic). `web/src/components/landing/Pond.tsx`: darker water and pads; fewer koi (about 3 big plus 4 small) swimming at about a third of the speed with lazier turns and a gentle flee; ripples travel at half speed and render as flat pixel rings (crest, trough, base) instead of a smooth gradient; softer pointer wake and smaller click splash; pads, duckweed and reeds respond less; two slower dragonflies; slower sway. `Landing.tsx`: no ripples on hover (only clicks and the Drop it button), no card lift. Headlines now Silkscreen Bold with a stepped pixel extrusion (`.pop-title` in `globals.css`).
In progress: nothing.
Next: customer "Review invitations" step; stage 8 memo.
Decisions: none new.
Blocked on: nothing.
Contracts touched: none.

Libraries and tools to credit in the README (rule 7), added: Silkscreen font (Google Fonts, SIL Open Font License).

## 2026-11-22 15:10 IST ananya landing-professional
Done: landing typography made minimal and professional (Ananya: "not a game"). Headlines in Instrument Serif with italic accents, body and buttons in Geist, small labels in Geist Mono; frosted-glass panels with thin borders; rounded pill buttons; calmer, plainer copy ("One question. Answers from the people who were there."). The two rule toys restyled to match. Removed Pixelify Sans, Silkscreen and every pixel-style class. The koi pond background is unchanged. Files: `web/src/components/landing/Landing.tsx`, `Toys.tsx`, `web/src/app/page.tsx`, `web/src/app/globals.css`.
In progress: nothing.
Next: push; customer "Review invitations" step; stage 8 memo.
Decisions: none new.
Blocked on: nothing.
Contracts touched: none.

Libraries and tools to credit in the README (rule 7), changed: Instrument Serif (Google Fonts, SIL Open Font License) replaces Pixelify Sans and Silkscreen.

## 2026-11-22 15:13 IST ananya landing-pond-tune
Done: `web/src/components/landing/Pond.tsx`: less clutter (about half the lily pads and dark pools, a third of the duckweed, three reed clumps instead of seven); darker water and pads plus a fixed shade over the pond, darkest behind the centre column, so text reads better; a clear ripple trail behind the pointer (stronger wake every frame, lower threshold for the ripple rings, slightly brighter crest).
In progress: nothing.
Next: push; customer "Review invitations" step; stage 8 memo.
Decisions: none new.
Blocked on: nothing.
Contracts touched: none.
