# Synex web (owner: Ananya)

## Scaffolding (credit in the final README)

Created on 2026-11-22 with the official Next.js generator (create-next-app, Next.js 16.4.6):

```
npx --yes create-next-app@latest web --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack --disable-git --yes
```

`AGENTS.md` is written by `next dev` itself.

## Run

```
npm install
npm run dev          # http://localhost:3000
```

The server must run on port 8000 (`cd server && .venv/bin/uvicorn app.main:app --port 8000`).
Set `NEXT_PUBLIC_SYNEX_API` to point somewhere else.

## Screens

| Route | Who | What |
| --- | --- | --- |
| `/` | customer | ask a question, recent cases |
| `/cases/[id]` | customer | live progress, cost counters, plan and anonymised panel |
| `/operator/approvals` | operator | approve or reject outreach drafts (shows real names) |

Customer screens never render a person's name, headline, profile URL or location (`src/lib/api.ts`).
