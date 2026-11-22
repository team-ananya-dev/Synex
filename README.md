# Synex

An expert network, rebuilt as software. A customer asks a business question. Synex finds former employees in live people data, screens every person and every answer with fixed compliance rules, invites a panel by email (to teammates only, in this competition), collects their answers, and returns them with a count of independent sources, a confidence level and a short summary where every sentence cites an answer.

Built at ContextCon 05 (theme "Services, Replaced") by Dev and Ananya.

## What is real, what is simulated

| | |
| --- | --- |
| **Real** | People and company data from the Crustdata API, every model call to the Claude API, the compliance rules, the response screen, the audit trail and the cost log. Nothing is pre-loaded, hard-coded or stored for the demo. |
| **Teammates play the experts** | Experts are members of our team. Every invitation goes to one of two teammate inboxes through a local mail server (Mailpit) and never to a real person. A teammate opens the private link and answers in the role of the candidate. |
| **No payments** | The service takes no payment and moves no money. The case page shows a quoted price in rupees, labelled "quoted price, no payment taken". The expert page shows a payout figure labelled simulated. |
| **Development limits** | While developing, a case sources only the first 2 sub-questions, 1 company each, and a search returns at most 5 people. `SYNEX_DEMO=1` turns every limit off, and also turns off the development cache of Crustdata responses. |

## How it works

Eight stages. Details and diagrams are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

| # | Stage | What it does | Decided by |
| --- | --- | --- | --- |
| 1 | Question screen | Allows, rewrites or refuses the question and says why. | small model |
| 2 | Plan | Splits the question into 3 to 5 sub-questions with the expertise and target companies. A company counts as "named" only if its name is in the question, checked in code. | small model, code check |
| 3 | Sourcing | Finds the company record by id, then searches Crustdata for people who held a role there that ended inside the window. | Crustdata; model only picks among returned ids |
| 4 | People screen | Fixed rules, each returning pass or fail with a reason. | code |
| 5 | Ranking | Scores each remaining person against the sub-question and must quote evidence from the profile. Code drops any quote it cannot find. | small model, code check |
| 6 | Invitations | Drafts one anonymised invitation per expert. The customer approves them before anything is sent. | small model, customer click |
| 7 | Response screen | Each answer is accepted, redacted, held for a team member, or rejected. | small model proposes, code verifies |
| 8 | Result | Counts independent sources, sets the label and confidence, and writes a short summary. | code, then small model for wording |

Every model call uses the small model (`claude-haiku-4-5-20251001`). The code has a setting for a larger model, but no stage uses it.

### People screen rules (stage 4)

Defaults: left at least 6 months ago, at most 24 months ago, at least 12 months at the company.

- not a current employee of the target company
- cooling-off (left at least 6 months ago)
- freshness (left at most 24 months ago)
- minimum tenure
- competitor conflict: a sensitive current role at a direct competitor fails the person; any other role at a competitor flags them for review; if the competitor list could not be fetched, everyone is flagged, never silently passed
- restricted list (the check exists; the list is empty, nobody is on it yet)
- sensitive former role (C-suite, legal, finance control, security and similar): flagged for review

Not built: the closed-period rule for listed companies and a do-not-contact table.

### Response screen (stage 7)

The model must quote the exact words it wants removed. Code checks that each quote appears in the answer; a reply that fails the check is retried once and then the answer is held for a person, never accepted. A code rule also looks for leak phrases ("confidential", "internal deck", "I shouldn't say" and similar) and holds an answer that contains one even if the model accepted it. "I don't know" and "I can't answer without confidential information" are recorded as rejected with that reason. A team member can accept or reject a held answer; nobody can edit text.

### Result (stage 8)

Sources, label and confidence are computed in code. Two answers count as one source when both experts worked at the same company, in the same function and city, with at least 3 months of overlap in their roles (Crustdata work history). A missing field counts the expert as a separate source and is listed. Confidence: 3 or more independent sources High, 2 Medium, 1 Low. The model only writes the summary wording and judges consensus or split; any sentence without a valid citation is dropped, and the count of dropped sentences is shown.

## Approvals

- The customer approves the plan. Nothing is fetched from Crustdata before that click.
- The customer reads the anonymised invitations and approves them with one click. Each email still gets its own approval event in the audit trail. Invitations with a review flag start unselected.
- Mail leaves only through one function that refuses any address not on a hard-coded allowlist of two teammate addresses (`server/app/actions/mail.py`).
- The customer never sees a name, a profile link, a city or an email address. Customer routes (`/customer/...`) are separate from operator routes, which do show them.

## Audit trail and cost log

Every state change, approval, screen verdict, mail event and model or Crustdata call is an event in a hash-chained, append-only table. The Audit trail page has a button that recomputes the whole chain and names the first changed event. The cost log lists every model call with tokens and dollars and every Crustdata call with credits. A per-case Crustdata credit cap and a $25 model budget are enforced in code.

## Run it

Needs Python 3 (we ran 3.14), [uv](https://github.com/astral-sh/uv), Node 20 or newer, and [Mailpit](https://github.com/axllent/mailpit).

```
cp .env.example .env          # fill CRUSTDATA_API_KEY and SYNEX_ANTHROPIC_KEY
cd server && uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python
SYNEX_DEV_CACHE=1 .venv/bin/uvicorn app.main:app --port 8000     # API docs at /docs
mailpit                                                          # SMTP 1025, inbox http://localhost:8025
cd ../web && npm install && npm run dev                          # http://localhost:3000
```

Never set `ANTHROPIC_API_KEY`; the app reads `SYNEX_ANTHROPIC_KEY`. For the final demo set `SYNEX_DEMO=1`.

Tests and checks:

```
cd server && .venv/bin/python -m pytest -q                       # server tests; no network, no spend
cd web && npm run lint && npx tsc --noEmit && npm run build
```

## Screens

| Route | Audience | What |
| --- | --- | --- |
| `/` | anyone | landing page |
| `/ask` | customer | ask a question |
| `/cases/{id}` | customer | plan and approval, invitations, live progress, answers, result, cost log |
| `/operator/approvals` | operator | held answers (accept or reject) and the invitation log |
| `/operator/audit` | operator | the event trail, chain check, cost log |
| `/expert/{token}` | expert | private link: rules, answer form, review, submit |

## Repository

```
server/   FastAPI app: core (database, audit chain, model wrapper), crustdata, stages 1 to 8, actions (mail gate, pricing), jobs (runner, routes), routes (expert, responses, result), tests
web/      Next.js app: customer, operator and expert screens, landing page
contracts/  agreed API, event and enum definitions, append-only
docs/     architecture, plan, progress logs, notes between the two builders
```

## Not built

The browser voice interview (the expert page is a form), the closed-period rule, a do-not-contact table, per-role city data (independence uses the profile's current city), and any real payment.

## Open questions for the organisers

- Is a development-time cache of real Crustdata responses allowed, if it is off for the finals run?
- Is a teammate typing a persona's answer on the expert page acceptable?
- Does one customer click on a batch of anonymised invitations count as "a person's approval" for each email? Until answered, this README describes it exactly as above and claims nothing more.

## How it was built

Written from empty folders during the build. `CLAUDE.md`, `.claude/` (three helper agents and two commands) and `docs/` (plan, rulebook, notes) were prepared before the build and contain no application code. Both builders used Claude Code, an AI coding tool. Commit history is unedited.

## Credits

**Backend (pip):** [FastAPI](https://github.com/fastapi/fastapi), [Uvicorn](https://github.com/encode/uvicorn), [httpx](https://github.com/encode/httpx), [pydantic](https://github.com/pydantic/pydantic) (a FastAPI dependency), [pytest](https://github.com/pytest-dev/pytest), the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python). Environment management with [uv](https://github.com/astral-sh/uv).

**Frontend (npm):** [Next.js](https://github.com/vercel/next.js) 16.4.6, [React](https://github.com/facebook/react) 19.3.0, [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) 4.3.3, [TypeScript](https://github.com/microsoft/TypeScript), [ESLint](https://github.com/eslint/eslint) with eslint-config-next.

**Fonts (Google Fonts, SIL Open Font License):** Geist, Geist Mono, Instrument Serif.

**Tools:** [Mailpit](https://github.com/axllent/mailpit) v1.34.0 (MIT) as the local inbox. Data from [Crustdata](https://crustdata.com). Models from [Anthropic](https://www.anthropic.com).

**Scaffolding commands run (rule 10):**

```
npx --yes create-next-app@latest web --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack --disable-git --yes
uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
```

Mailpit was downloaded from its GitHub release page and its checksum was checked.

**Landing page:** the pond is drawn in code on a canvas with no image files. Its look was inspired by a pixel-art koi pond illustration and by the playful feel of other pixel games; no art, code or assets were copied.
