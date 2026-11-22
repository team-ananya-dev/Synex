# Synex: project context (self-contained)

This file carries everything decided in the planning chat, because that chat is not available to the agents. Read it fully at the start of a new session. Where it conflicts with a longer document in this folder, the rulebook (`01_RULEBOOK.txt`) wins, then this file, then the others.

Written Sunday 22 Nov 2026, before kickoff. Nothing is built yet.

## 1. The event

- ContextCon 05, run by Crustdata with Y Combinator, at BITS Pilani. Build day is Sunday 22 Nov 2026. Theme: "Services, Replaced" (build an agent on live web data that replaces a paid service).
- The build is 7 hours, from scratch, in the organiser repository, with commits throughout. Code freeze at the end of the build.
- Deliverables, all in the organiser repo before freeze: code, README, architecture diagram, demo video. Finals include a live demo, a live fix and a design question (judges test whether we understand our own code).
- Top 3 teams get a 1:1 YC office hour with Jon Xu. Prize pool about $12K. Crustdata gives 15,000 API credits.
- Jon Xu's background is fintech, AI and investing, which is why the idea targets investing research.
- The rulebook has hard rules. The ones that shape everything are in section 2 below.

## 2. Rules that cannot be broken (from the rulebook)

1. Planning is allowed before the build. Writing code before the official start is not (disqualification).
2. Code from earlier events or earlier projects is not allowed (disqualification). That includes our own old repos. Start from empty folders. Official scaffolding commands (for example the Next.js generator) are fine if credited.
3. Open-source code is allowed if the licence allows it and the README names it.
4. AI coding tools are allowed. The team must understand its own code. Judges test it in the live fix and design question.
5. Agents interact only with the team's own environment and permitted APIs.
6. Agents never contact real people. Teammates play the client, the vendors, the candidates and other counterparties (disqualification if broken).
7. Any action that cannot be undone, such as a payment or an email, waits for a person's approval.
8. Only registered team members write code, prepare content or operate the service. Judges, friends and other teams cannot play roles.
9. No hard-coded answers, no stored results. No results entered by hand during a run: a person can only approve or reject actions.
10. No faking a demonstration: no recorded output, no mock presented as live, no result prepared in advance.
11. No claims in the README or on stage that the service does not do.
12. No changing commit history, timestamps, logs or cost records.
13. No trying to obtain the unseen requests or other hidden content (including by asking organisers).
14. No sharing API keys or repo access with another team.

Practical meaning: caching real API responses while developing is a grey area (ask the help desk); everything shown in the demo must come from live calls; the audit trail and cost log are append-only and never edited.

## 3. What Synex is, in plain words

An expert network is a company that finds you a person who used to work somewhere and sells you an hour on the phone with them. Hedge funds, private-equity firms and consultants buy these calls before big decisions. The big names are GLG, AlphaSights, Guidepoint, Tegus (AlphaSense), and newer ones such as Ethos and Qualitate. Prices are roughly $500 to $1,500 or more per call hour (figure from earlier research, unverified for this build).

Today's flow: an analyst emails a question to an account manager; staff search a database and LinkedIn for suitable people; each candidate is vetted by hand (are they still employed there, did they leave recently, does an NDA block it); staff recruit and schedule; the analyst runs the call.

Synex does the sourcing and vetting by software. A customer types a question. Synex finds former employees from Crustdata's people data, screens them with fixed compliance rules, contacts a panel in parallel, collects their answers by form or voice, screens each answer, and returns one cited memo with an audit trail.

The wedge (what makes it different): incumbents add AI interviewers, but they still start from their own database of registered experts. Synex sources cold experts on demand from a live people graph, builds compliance into every step, and combines many experts' answers instead of one call.

## 4. How it differs from GLG

| Aspect | Expert network | Synex |
| --- | --- | --- |
| Finding experts | Staff search a database and personal contacts | Software searches a live people graph by company, role and tenure |
| Vetting | Manual checks by staff | Fixed rules in code, each with a stated reason |
| Contact | One expert, scheduled call | A panel contacted in parallel; each chooses form, doc or voice |
| Output | Call notes by the analyst | One memo that combines many answers, with confidence and sources |
| Paperwork | Opaque | Audit trail of every decision |
| Cost model | Per hour | Per answered sub-question, held first and captured only when answered |

Objection and answer: "Why would a cold expert answer, and for free?" They are not asked for free: experts are paid per accepted answer. The ask is small (a form, not a scheduled hour), they pick the format, and we contact many people at once so we never depend on one reply.

## 5. The product (real-world version)

Customer: asks a question, reviews a plan and a ranked panel, approves the spend, watches answers arrive on a live case page, reads the memo, can open the audit trail.

Expert: receives an email with a private link, sees the sub-questions and the rules (no confidential information; answers are screened; payment terms), chooses form, document or voice, and submits. Payout follows an accepted response.

Operator (a teammate in the hackathon): approves or rejects each drafted email and payment in the approval queue.

Pricing logic (real product): hold funds when the plan is approved; capture only for a sub-question with at least 2 independent accepted responses; single-source sub-questions are charged at a reduced rate or delivered free (rate undecided); release the rest. Experts are paid per accepted response after screening. In the hackathon this is a simulated ledger, labelled "simulated".

## 6. The pipeline (eight stages)

1. Question screen: allow, refuse (with reason) or rewrite. Refuse requests for non-public information about a named company. Small model.
2. Decomposer: 3 to 5 sub-questions, the expertise needed, the target companies. Small model.
3. Sourcer: Crustdata search for people. No model.
4. People screen: rules in plain code (section 7). No model.
5. Ranker: score and one-line reason per candidate. Small model.
6. Outreach writer: email draft and expert-page link per expert; goes to the approval queue. Small model.
7. Response screen: accepted, redacted, held or rejected for each answer. Small model.
8. Memo writer: cited memo with confidence per sub-question. Large model. A checker in code removes any claim whose source ids do not exist (cite or drop).

Stages 1 to 6 run as one job per case; stages 7 and 8 run whenever a new answer arrives, so the memo updates live. Every stage writes its result to the database and emits an event on the live stream.

## 7. Compliance rules

People screen, one function per rule, each returning pass or fail and a one-line reason:

1. Not a current employee of the target company.
2. Cooling-off: left at least 6 months ago.
3. Freshness: left no more than 24 months ago.
4. No competitor conflict: not now in a sensitive role at a direct competitor or listed partner.
5. Restricted list: not on the hard-coded restricted list.
6. Sensitive former role (C-suite, board, legal, investor relations, finance control, security): flag for manual review.
7. Closed period: if the target is publicly listed, flag a call inside the configured pre-earnings blackout window.

Also: a do-not-contact table. A failed person leaves the shortlist and the reason is shown to the customer.

Response screen verdicts: accepted (goes into the memo), redacted (flagged span removed), held (waits for a teammate's approve or reject), rejected (excluded, reason logged). A person may approve or reject; nobody edits text.

Anonymity: if fewer than 3 accepted experts share a role label, coarsen the label in the memo.

## 8. Synthesis rules (in code, not left to the model)

- Group accepted answers by sub-question.
- Independent sources only: two experts with the same company, function and city and at least 3 months overlap count as one source.
- Label each finding: consensus (2 or more independent sources agree), split (they disagree; show both), single source (weaker).
- Confidence: High with 3 or more independent agreeing sources, Medium with 2, Low with 1. Computed in code and passed to the model, which only writes the wording.
- Compare findings with Crustdata company data where possible: "agrees", "conflicts" or "no data". A conflict caps confidence at Low.
- Every claim carries source ids: an accepted response, a Crustdata record, or a fetched page (if web fetch turns out to be permitted).
- If a sub-question has no accepted answer, the memo says so.

## 9. Crustdata

Crustdata is the data sponsor: a live people and company data provider. The public API has three areas: Company (identify, autocomplete, enrich, search), Person (search, enrich) and Web (search, fetch). Requests carry `Authorization: Bearer <key>` and `x-api-version: 2025-11-01`. Confirm against the docs on the day.

Unknowns to test in the first 45 minutes, on 3 companies (one Indian and not a household name):

1. Can person search filter by past employer?
2. Does a profile show when someone left?
3. Does it return emails? (Not needed: outreach goes only to teammates.)
4. What do one search and one enrich cost in credits?
5. Is the data live or indexed?
6. Does company enrich return function-level headcount or only total headcount?

If past-employer filtering or exit dates are missing: search by company and title, filter work history in code, and mark exit date "unverified". If coverage is thin: the memo says what is missing. It never invents people.

Every Crustdata record cited in a memo is stored with its call id. A per-case credit cap is shown in the UI.

## 10. Hackathon scope

Build for real: ask and plan, question screen, Crustdata sourcing, people screen, ranking, approval queue, expert page with form, response screen, live case page, synthesis and memo, audit trail and cost log.

Build if time allows: browser voice interview with leak refusal (typed chat is its fallback), Crustdata company-data cross-check.

Simulate and label: payments and payouts (a ledger of holds, captures and payouts released by an approve click, marked "simulated" in the UI and README).

Restrict: email goes only to a hard-coded teammate allowlist, enforced in code, with a visible refusal for any other address. Default mail path is Mailpit (a local inbox). Gmail SMTP only if the help desk confirms it is a permitted API.

Do not build: customer signup (one pre-made account), document upload, reviewer queue, delivery tracking, expert profiles, follow-up questions, multiple organisations, refund logic beyond the ledger, privacy and legal tooling.

### Persona routing (important design detail)

Only registered team members can operate the service, so the "experts" are teammates. With two people, the shortlist can contain, say, five Crustdata candidates, but every outreach email goes to a teammate's inbox. Each outreach has its own random-token link. The teammate answers on that page in the persona of that candidate. Independence in the memo is computed from the candidate's profile data (company, function, city, overlap), not from who typed. Open question for the help desk: whether typing a persona's answer on the expert page is acceptable (rule 3.3) rather than "entering results by hand" (rule 5.5). Our reading: counterparties' replies are inputs; the system's results (candidate list, screens, memo) are never entered by hand.

The voice interview is a teammate speaking as the persona. During a refusal test, the teammate tries to get the agent to reveal confidential information (what other experts said, who the client is). The agent declines out loud and logs a refusal event.

## 11. Architecture and data model (summary; the build guide has the drawing)

One FastAPI server runs the stages, calls Crustdata and Claude through logging wrappers, and writes everything to SQLite. A Next.js web app has the customer screens, the approval queue and the expert page. The browser receives progress over one server-sent-events stream per case. Mail leaves only through the action gate.

Tables: cases, subquestions, candidates, screen_results, outreach, responses, response_screens, findings, ledger, events (append-only, hash-chained: each event stores the previous event's hash and its own), llm_calls (cost log).

Case states: DRAFT, PLANNED, SOURCING, AWAITING_APPROVAL, COLLECTING, SYNTHESIZING, DELIVERED, REFUSED or FAILED.

Screens: ask; plan and panel; approval queue; live case; memo; audit trail and cost log; expert page.

## 12. LLM and budget

- Claude Code agents (writing our code) run on each person's Claude Pro subscription. Never set `ANTHROPIC_API_KEY` in a shell where Claude Code runs; it would switch to API billing.
- The running app uses the shared $25 Claude API key from `SYNEX_ANTHROPIC_KEY` in `.env`.
- Small model for stages 1, 2, 5, 6, 7 and the voice interviewer's turns. Large model only for the memo. Keep about $5 in reserve for the finals run.
- One wrapper function makes every model call: purpose label, prompt, JSON schema, validation, one retry, log to llm_calls. Replies are structured JSON.
- Read current per-token prices from the Anthropic console at kickoff. Do not assume them.

## 13. Voice

Free only. Chrome's SpeechRecognition for input, Claude for the reply, `speechSynthesis` for output. Chrome only; the voice sounds robotic. As far as we know, Chrome's recognition sends audio to Google's servers; ask the help desk whether that counts as a permitted API. Typed chat with the same interviewer is the fallback and is labelled as text. Open-source speech models (faster-whisper, Piper) are a stretch and must be credited.

## 14. Team and ownership

Two builders: Dev (Ubuntu) and Ananya (Windows, WSL 2). Dev owns pipeline, Crustdata, compliance, actions, audit and cost log. Ananya owns the web app, the expert page, voice, the response screen and the memo writer. Ownership is by directory and file; see `docs/TEAM_README.md` section 3. Each person runs their own Claude Code sessions on their own laptop.

Commit-message rule (Dev's preference, applied to the repo): no Claude, co-author or "generated with" lines.

## 15. Decisions already made, with reasons

| Decision | Reason |
| --- | --- |
| Theme on the portal | "Your own idea". Research and markets, Trust and compliance and Investing each replace a different service (research firms, KYB screening, scouts and diligence) with their own deliverables, so they do not fit. The one-line description entered on the portal is deliberately vague so other teams cannot copy the approach. |
| Idea: Synex (spoken hook "GLG in a Box") | Matches the sponsor's people data and Jon Xu's field; replaces a real expensive service. |
| Panel of many experts, not one call | Removes dependence on a single reply and creates the multi-expert synthesis incumbents do not offer. |
| Compliance as plain code with stated reasons | Fast, repeatable, explainable on stage, and judges can read it. |
| Payments are a simulated ledger | Real payment gateways are irreversible and out of scope; the approve click shows the control. |
| Teammate-only email allowlist enforced in code | Rulebook: agents never contact real people. |
| Mailpit as the default mail path | Stays inside our own environment; no extra API to justify. |
| Cache of real API responses only while developing, off for the finals | Avoids "stored results" accusations; confirm with the help desk. |
| Free browser voice | No paid voice tools available. |
| Two-person scope with an early cut list | Four-person plan does not fit two people. |

## 16. Open questions

For the help desk at kickoff:
1. Which APIs are permitted: Crustdata and the Claude API, plus web search and fetch, Gmail SMTP, and Chrome's built-in speech recognition?
2. Is a development-time cache of real API responses allowed if it is off for the finals run?
3. Is a teammate typing a persona's answer on the expert page acceptable?
4. Are instruction files (`CLAUDE.md`, `.claude/`) prepared before kickoff allowed if we say so in the README?

Do not ask about the content of the finals' unseen requests (rule 5.9).

For us, in the first hour: the Crustdata coverage test (section 9), the price per answered sub-question, and the single-source rate.

## 17. Things agents must not do

- Write code before the build start is confirmed by a human.
- Copy code from earlier projects or other teams.
- Add case-specific logic (no "if Zepto").
- Add a real payment provider or any path that emails a non-allowlisted address.
- Edit logs, the audit trail or the cost log, or rewrite git history.
- Hard-code or store results, or present fixtures as live.
- Edit files owned by the other person.

## 18. Glossary

- **Expert network:** a company that sells calls with former employees.
- **Panel:** the set of experts contacted for one case.
- **Sub-question:** one piece of the customer's question that a specific kind of expert can answer.
- **Independent source:** an expert whose background does not overlap another's enough to make their answers duplicates.
- **Approval queue:** list of drafted emails and payments that wait for a human click.
- **Allowlist:** the hard-coded list of teammate email addresses that mail may go to.
- **Cite or drop:** a memo claim without valid source ids is removed before display.
- **Audit trail:** append-only, hash-chained event log.
- **Cost log:** record of each model call and Crustdata call with tokens or credits and dollars.
