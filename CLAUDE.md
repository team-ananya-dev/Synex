# Synex: agent instructions

Every Claude Code session in this repo reads this file first. Repo: git@github.com:team-ananya-dev/Synex.git. Older documents call the project "Primary"; that is the same project, now named Synex. Keep it short. Detail lives in `docs/TEAM_README.md`.

## What this project is

Synex (ContextCon 05, theme "Services, Replaced") replaces an expert network. A customer asks a business question. The system finds former employees through Crustdata, screens them with fixed compliance rules, drafts outreach into an approval queue, collects answers (web form or free browser voice), screens each answer, and writes a cited memo with an audit trail and cost log.

Full context: `docs/context/00_PROJECT_CONTEXT.md` (self-contained summary of every decision so far), `docs/context/` (rulebook, build guide, site flow, brief) and `docs/TEAM_README.md`. Read the context file and the build guide before designing anything.

Other files: `docs/AGENT_COMMS.md` (how we stay in sync), `docs/SETUP_RUNBOOK.md` (human-only setup), `docs/KICKOFF_PROMPTS.md`.

## Who is working here

Two people, each with their own agents: Dev and Ananya. The person tells you who they are in their first message. If they do not, ask once. You may only edit files your person owns (table in `docs/TEAM_README.md`, section 3).

## Hard rules (competition rulebook; breaking these can disqualify us)

1. No code is written before the 7-hour build starts. If the build has not started, only discuss and plan.
2. Never contact real people. Email goes only to the teammate allowlist, enforced in code.
3. Every email and every payment goes through the approval queue and needs a human click. Payments are a simulated ledger and are labelled "simulated".
4. No hard-coded, stored or hand-entered results. No mock shown as if live. A cache of real API responses is for development only and is off for the demo.
5. The pipeline must work for any company and question. No case-specific logic (no "if Zepto").
6. Git history is never rewritten. No force push, no rebasing of pushed commits.
7. Credit every open-source library in the README. Claims in the README must match what the code does.
8. Free tools only for voice (Chrome speech APIs). Claude API budget for the running app is $25: small model for bulk stages, large model only for the memo, every call logged.
9. Only registered team members operate the service. A person's role in a run is to approve or reject actions, or to answer as a persona on the expert page. Nobody types or edits results, the audit trail, or the cost log.
10. Start from empty folders. No code from earlier events, earlier projects, or other teams. Use official scaffolding only and record each command so the README can credit it.
11. The default mail path is Mailpit (a local inbox). Do not add Gmail SMTP or any other outside service unless the humans say the help desk confirmed it.

## Working rules

- Stay in your owned directories. If you need a change elsewhere, write a request file in `docs/inbox/<owner>/` (a new file, never an edit). Do not edit the other person's code.
- Run `/sync` at the start of every task and before every push. It shows what the other person pushed. Run `/handoff` when you stop.
- If another of the user's sessions needs to know something, message it by name (see `docs/AGENT_COMMS.md`) and name the file to read. Never send long text or secrets in a message.
- Shared contracts live in `contracts/`. Append-only. A change to an existing contract needs a message to the other person first, then a small commit pushed straight away.
- Commit small and often. Push at least every 30 to 45 minutes.
- Commit message format: `<area>: <what changed>`, area is `server`, `web`, `contracts` or `docs`. No Claude, co-author or "generated with" lines in commit messages. After your first commit, run `git log -1` and check.
- Before every push run the checks in `docs/TEAM_README.md`, section 7.
- When you stop, append to your progress log `docs/progress/<name>.md` using the template in section 10 of the team README.
- The Claude API key for the running app is `SYNEX_ANTHROPIC_KEY` in `.env`. Never set `ANTHROPIC_API_KEY` in a shell where Claude Code runs: it would switch Claude Code from the subscription to the API key and spend the $25.
- Never commit `.env`, keys, or anything under `.claude/settings.local.json`.

## Commands

To be filled in once the skeleton exists (around 0:45). Until then, run nothing that assumes a stack.

- Server: `TBD`
- Web: `TBD`
- Tests: `TBD`
