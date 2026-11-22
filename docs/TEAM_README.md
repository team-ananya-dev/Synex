# Synex: team README (Dev and Ananya)

How we work together, how each of us runs Claude Code agents, how we avoid merge conflicts, and how context moves between people and sessions. This is the working document for the build. It is not the final submission README.

Status when written: Sunday 22 Nov 2026, before kickoff. Nothing in the repo exists yet. The rulebook bans pre-written code, so everything below is plan and setup. Files are copied into the organiser repo at 0:00.

---

## 1. What we are building (one screen)

Synex answers one business question with a cited memo built from several former employees' answers. Every step runs live in the 7-hour build.

1. Customer types a question.
2. System splits it into sub-questions and picks the expertise needed.
3. It finds former employees through Crustdata and ranks them.
4. Fixed compliance rules screen the question, each person and each answer.
5. Outreach drafts wait in an approval queue. A teammate approves; mail goes only to a teammate allowlist.
6. Experts answer by web form or by free browser voice.
7. Each answer is screened, then the memo is written with a source on every claim, an audit trail and a cost log.

The full spec is in `docs/context/` (exported from the build guide, the site-flow document and the brief). Read the build guide first.

## 2. Rules that cannot be broken

These come from the Participant Rulebook. Agents read the same list in `CLAUDE.md`.

| Rule | What it means |
| --- | --- |
| 7-hour build, no pre-written code | Before kickoff: plan only. We copy docs and instruction files in at 0:00 and say so in the README. |
| Agents never contact real people | Teammates play the experts. Email only to the allowlist, enforced in code. |
| Only registered team members operate the service | Judges, friends and other teams cannot play the experts. A person's role in a run is to approve or reject actions, or to answer as a persona on the expert page. Nobody types or edits results. |
| From scratch, our own code | No code from earlier events or earlier projects, including our own old repos. Use official scaffolding commands and credit them in the README. |
| Irreversible actions need a human | Emails and payments sit in the approval queue until a person clicks approve. Payments are a labelled simulated ledger. |
| No stored, hard-coded or hand-entered results; no mocks shown as live | A cache of real API responses is for development only and is off for the finals run. |
| Unseen requests at the finals | No case-specific logic. Test on a second company before 6:15. |
| Commit throughout; history is not rewritten | No force push. No rebase of anything already pushed. |
| README is honest and credits open source | List every library. State what is simulated. |
| Live fix and design question at the finals | Both of us must be able to explain every module. See section 11. |

## 3. Who owns what

Two people cover the four roles from the build guide. Dev takes roles A and B (pipeline, compliance, actions). Ananya takes roles C and D (interface, expert side, synthesis). You may change this split, but decide it in the first 15 minutes and write it down in `contracts/OWNERS.md`.

Ownership is by directory and by file name. Only the owner edits a file. This is the main way we avoid merge conflicts.

| Area | Owner |
| --- | --- |
| `server/app/core/` (database, config, event bus, model wrapper, cost log, audit hash chain) | Dev |
| `server/app/crustdata/` | Dev |
| `server/app/stages/` stages 1 to 6 (question screen, decomposer, sourcer, people screen, ranker, outreach) | Dev |
| `server/app/actions/` (approval queue, mail send, simulated ledger) | Dev |
| `server/app/jobs/` and the live-update stream route | Dev |
| `server/app/db/schema_core.sql` | Dev |
| `server/requirements/core.txt` | Dev |
| `.env.example`, `.gitignore`, `.gitattributes`, top-level config | Dev |
| `web/` everything (all screens, expert page, voice client in the browser) | Ananya |
| `server/app/stages/` stages 7 and 8 (response screen, memo writer, citation checker) | Ananya |
| `server/app/interview/` and `server/app/routes/expert.py` | Ananya |
| `server/app/db/schema_expert.sql` | Ananya |
| `server/requirements/expert.txt` | Ananya |
| `web/package.json` and its lockfile | Ananya |
| `contracts/` | Shared, append-only (section 8) |
| `docs/progress/dev.md` | Dev |
| `docs/progress/ananya.md` | Ananya |
| `docs/inbox/<name>/` | Anyone writes new files; only `<name>` reads and archives |
| Final `README.md`, architecture diagram, demo video | Both, in the last 45 minutes, one section each |

Stage files are named so ownership is clear from the name, for example `s3_sourcer.py` (Dev) and `s7_response_screen.py` (Ananya).

### Scope with two people

The build guide assumed four people. Two people means we must cut earlier. The 5:15 milestone is one full case running live from question to cited memo. If we are behind at 2:30, cut in this order:

1. Free open-source speech models (stay on Chrome speech).
2. The company-data cross-check in the memo.
3. The audit hash-chain verify button (keep the plain event list).
4. Voice mode entirely (form plus typed chat, labelled honestly).

Never cut: the approval queue, the email allowlist and its refusal, the response screen, cite-or-drop, the README, the demo video.

## 4. Setup

### 4.1 Dev (Ubuntu)

1. Install system packages: `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip curl build-essential`.
2. Install Node 20 or newer. Use nvm, following the instructions on the nvm GitHub page.
3. Install Claude Code with the native installer: `curl -fsSL https://claude.ai/install.sh | bash`, then run `claude doctor`.
4. Run `claude`, choose the subscription login (Claude Pro), and finish the browser sign-in.
5. Set your git identity: `git config --global user.name "Dev"` and `git config --global user.email "<your email>"`.
6. Set up SSH keys or a GitHub token for the organiser repo, depending on how they give access.

### 4.2 Ananya (Windows)

Recommended: WSL 2 with Ubuntu. Then every command in this document works unchanged, and Claude Code's command sandboxing is supported there.

1. Open PowerShell as Administrator and run `wsl --install`. Restart if asked. Open the Ubuntu app and create a Linux user.
2. Check the version with `wsl --list --verbose`. If Ubuntu shows version 1, run `wsl --set-version Ubuntu 2` (use the name shown in the list).
3. Inside Ubuntu, follow section 4.1 steps 1 to 5. Install and run `claude` inside the WSL terminal, not from PowerShell.
4. Keep the repo inside the Linux file system (for example `~/Synex`), not under `/mnt/c`. Cross-system paths are slow and cause line-ending and permission problems.
5. Use VS Code with the WSL extension if you want a graphical editor.

Fallback if WSL 2 fails within 15 minutes (virtualisation off in BIOS, for example): native Windows. Install Git for Windows, run the PowerShell install command from the Claude Code setup page, and run `claude doctor`. Native Windows works, but command sandboxing is not supported there, and line endings need care (section 12). Do not spend more than 15 minutes on this; ask Dev for help.

### 4.3 Both

- Confirm the Claude Pro login works: run `claude`, then `/status` to see your usage.
- Do not set the `ANTHROPIC_API_KEY` environment variable in any shell where you run Claude Code. If it is set, Claude Code uses that key instead of your subscription and spends API credit. See section 5.
- Install `gh` (GitHub CLI) if you want to open pull requests; plain `git` is enough for our workflow.
- Create `.env` from `.env.example` once the repo exists. Never commit `.env`.

## 5. Two different Claude budgets (do not mix them)

| Use | Where it is paid from | Notes |
| --- | --- | --- |
| Claude Code agents that write our code | Each person's Claude Pro subscription | Pro has a five-hour session limit and a weekly limit, shared with Claude chat. Running several agents at once uses it up faster. Check `/status`. |
| The running Synex app (decomposer, ranker, screens, memo, voice turns) | The shared $25 Claude API key | Small model for bulk stages, large model only for the memo. Every call is logged in `llm_calls`. |

The trap: if `ANTHROPIC_API_KEY` is set when you start Claude Code, Claude Code can use it instead of your subscription. Anthropic's support page says this explicitly. To avoid it, our app reads the key from a differently named variable, `SYNEX_ANTHROPIC_KEY`, set in `.env` and loaded by the app only. Never export it in your shell profile.

If a Pro session hits its limit mid-task, the wrap-up is short. Commit and push before you start any long task, and write the progress note (section 10) at least once an hour.

## 6. Repo layout (planned; created after kickoff)

```
Synex/
  CLAUDE.md                  agent instructions (this team)
  README.md                  final submission README (written in the last 45 minutes)
  .gitignore  .gitattributes  .env.example
  contracts/                 shared, append-only: OWNERS.md, API.md, EVENTS.md, ENUMS.md
    decisions/               one new file per decision: <date>-<who>-<topic>.md
  docs/
    TEAM_README.md           this file
    SETUP_RUNBOOK.md         human-only setup steps (accounts, keys, wiring checks)
    AGENT_COMMS.md           how agents and people stay in sync
    KICKOFF_PROMPTS.md       the first prompts for each person's Claude Code
    context/                 exported build guide, site flow, brief
    progress/dev.md          Dev's handoff log
    progress/ananya.md       Ananya's handoff log
    inbox/dev/               requests addressed to Dev (new files only)
    inbox/ananya/            requests addressed to Ananya (new files only)
  server/
    requirements/core.txt  requirements/expert.txt  requirements.txt
    app/
      main.py
      core/  crustdata/  actions/  jobs/        (Dev)
      stages/s1_..s6_ (Dev)   s7_, s8_ (Ananya)
      interview/  routes/expert.py              (Ananya)
      db/schema_core.sql (Dev)  schema_expert.sql (Ananya)
  web/                                          (Ananya)
  .claude/
    agents/                  shared subagent definitions (section 9)
    commands/                /sync and /handoff (see docs/AGENT_COMMS.md)
    worktrees/               ignored by git
```

`server/requirements.txt` only contains two lines that include the two files in `requirements/`. That way each of us edits our own dependency file.

## 7. Git workflow

### 7.1 Principles

- One remote (the organiser repo), one shared branch `main`.
- Short-lived branches. Nothing lives longer than about an hour before it reaches `main`.
- Rebase local, unpushed commits onto `origin/main` before pushing. Never rebase or amend anything already pushed.
- No force push. Ever. The rulebook forbids rewriting history.
- Small commits, pushed at least every 30 to 45 minutes. Push before the other person needs something from you.
- Commit message format: `<area>: <what changed>` with area `server`, `web`, `contracts` or `docs`.
- No Claude, co-author or "generated with" lines in commit messages. This is a team rule from Dev's preference; if Ananya prefers otherwise, change this line together.

### 7.2 Start of the build

```
git clone git@github.com:team-ananya-dev/Synex.git
cd Synex
git config core.autocrlf input        # Linux and WSL. Native Windows: see section 12
git switch -c setup/<yourname>        # only for the very first setup commit
```

Dev pushes the first commit (`.gitignore`, `.gitattributes`, empty folders with `.gitkeep`, `CLAUDE.md`, this file, `docs/context/`) straight to `main`. Ananya clones after that push.

### 7.3 Daily loop for one person (one agent)

```
git switch main && git pull --ff-only
git switch -c <name>/<task>            # example: dev/sourcer
# ... work, commit small ...
git fetch origin
git rebase origin/main                 # your local branch only
git switch main && git pull --ff-only
git merge --ff-only <name>/<task>
git push origin main
```

If `git push` is rejected because the other person pushed first: `git pull --rebase origin main`, then push again. Do not use `--force`.

### 7.4 Parallel agents: one worktree per agent

A worktree is a second working folder for the same repo, on its own branch. Agents in different worktrees cannot overwrite each other's files.

```
git worktree add ../Synex-wt-sourcer -b dev/sourcer origin/main
cd ../Synex-wt-sourcer
claude                                  # a separate Claude Code session in this folder
```

Claude Code also has a `--worktree` flag that creates a worktree for you under `.claude/worktrees/`. Check `claude --help` for the current syntax. Whichever way you create them, add `.claude/worktrees/` to `.gitignore`.

When a worktree's task is done, merge it as in 7.3, then clean up: `git worktree remove ../Synex-wt-sourcer` and `git branch -d dev/sourcer`.

### 7.5 Checks before every push (the agent runs these)

1. `git status`: nothing unexpected staged, no `.env`, no keys.
2. Only files you own changed: `git diff --name-only origin/main...HEAD` and compare with section 3.
3. The project's tests pass (command in `CLAUDE.md` once it exists).
4. No stored results, hard-coded company names or fixture data slipped in: search for the target company's name in `server/`.
5. `git log -1` shows no Claude or co-author line.

## 8. How we avoid merge conflicts

1. **Ownership by file.** Section 3 is the rule. A file has one owner.
2. **Contracts first.** In the first 15 to 20 minutes, together, write `contracts/`: API routes and JSON shapes (`API.md`), event types for the live stream (`EVENTS.md`), status values (`ENUMS.md`), table ownership (`OWNERS.md`). After that, each of us builds against the contract.
3. **Contracts are append-only.** Add new items freely. To change or remove an existing one, message the other person first, make the change in one small commit, and push immediately.
4. **Separate files for shared concerns.** Two schema files, two requirements files, two progress logs, separate stage files. Two people never edit the same file.
5. **Requests, not edits.** If you need something changed in the other person's area, write `docs/inbox/<owner>/<time>-<topic>.md` (what you need, why, and a deadline) and message them. New files never conflict.
6. **One formatter configuration.** Dev adds formatter settings in the first commit (the web app's default formatter and one Python formatter). No one reformats files they do not own.
7. **No generated or lock files edited by hand.** Ananya owns `package-lock.json`; Dev owns Python lock files if any. If you need a new dependency in the other person's area, send a request.
8. **Walking skeleton by 0:45.** Dev has real (not fake) endpoints returning data from live calls by 0:45, so Ananya builds against the live API instead of mock data. If a mock is unavoidable, it lives behind a clearly labelled flag, shows a "fixture data" banner, is listed in the README as a development aid, and is deleted before 6:15. Ask the help desk first.
9. **Pull before you start, push before you stop.** Every work session starts with `git pull --ff-only` and ends with a push or a note about why not.
10. **When a conflict does happen:** stop, tell the other person, resolve it together on a call, run the tests, push. Do not let an agent resolve a conflict in a file it does not own.

## 9. Multi-agent setup for each person

Claude Code offers three ways to run more than one agent. Use them in this order of simplicity.

| Level | What it is | Use it for | Limits |
| --- | --- | --- | --- |
| 1. Subagents | Helper agents inside one session, each with its own instructions and tools, defined in `.claude/agents/` | Read-only review, searching, testing, writing a doc | They share your session's usage. They help keep the lead agent's context clean; they do not make work run longer. |
| 2. Worktree sessions | Separate `claude` sessions in separate worktrees (section 7.4) | Two independent modules at once, for example sourcer and approval queue | Each session uses your Pro limit. Stay at two sessions per person. |
| 3. Agent teams | Several sessions that coordinate with each other | Not recommended for this build | The Claude Code docs say teams work best when tasks are independent and are a poor fit for same-file edits and tightly dependent work. Our time is 7 hours and the limits are shared. |

Our recommendation: each person runs one lead session in the main worktree plus, when two independent tasks exist, a second session in a worktree. Use subagents for review and checks.

### 9.1 Subagent definitions (copy into `.claude/agents/` at kickoff)

Create one file per agent. Keep them short. Frontmatter fields are `name`, `description` and `tools`.

`.claude/agents/rule-checker.md`

```
---
name: rule-checker
description: Read-only audit of staged changes against the competition rules. Use before every push.
tools: Read, Grep, Glob, Bash
---
You review changes, you never edit files. Check the diff against origin/main for:
1. any hard-coded company names, results, or fixture data presented as live;
2. any code path that can send email to a non-allowlisted address;
3. any email or payment that skips the approval queue;
4. any call to a paid voice service;
5. files outside the committer's owned directories (see docs/TEAM_README.md section 3);
6. secrets, .env contents, or ANTHROPIC_API_KEY use;
7. commit messages containing Claude or co-author lines.
Report each finding with file and line, or say "clean".
```

`.claude/agents/explorer.md`

```
---
name: explorer
description: Read-only code and docs search. Use to answer "where is X" or "what does contracts/ say about Y" without filling the main context.
tools: Read, Grep, Glob
---
Search the repo and docs/context/ and answer in under 200 words with file paths. Never edit files.
```

`.claude/agents/test-runner.md`

```
---
name: test-runner
description: Runs the project's tests and reports only failures with the smallest relevant output.
tools: Read, Grep, Glob, Bash
---
Run the test commands listed in CLAUDE.md. Report pass or fail, and for each failure the test name, the error line, and the file. Do not fix anything.
```

You can add a model line to a subagent's frontmatter if you want a smaller model for read-only helpers; check the Claude Code documentation for the current field names.

### 9.2 Suggested sessions

Dev: lead session on pipeline and Crustdata; second worktree session for the approval queue and mail send once contracts exist.

Ananya: lead session on web screens; second worktree session for stages 7 and 8 (response screen and memo) once the contracts for responses and findings exist.

### 9.3 Keeping the Pro limits alive

- Start each task with a clear prompt and the files to read. Do not let agents explore the whole repo.
- Keep `CLAUDE.md` short. Put long material in `docs/context/` and tell the agent which file to read.
- Do not leave sessions idle in a loop. Close a worktree session when its task merges.
- Run `/status` at the start of each hour. If you are close to a limit, tell the other person and switch to the plan or documentation tasks.

## 10. Transferring context

Context moves through files, never through chat history. A new session, a new agent, or the other person should be able to start from the files alone.

### 10.1 What carries context

1. `CLAUDE.md`: loaded automatically by every session.
2. `docs/context/`: the build guide, the site flow and the brief. Export them right after the repo opens (the documents export to Markdown; the brief is a PDF).
3. `contracts/`: the agreed interfaces.
4. `docs/progress/<name>.md`: your handoff log. Append only.
5. `docs/inbox/<name>/`: requests from the other person.
6. Git history: small commits with clear messages.

### 10.2 Handoff log template (append at the end of every session)

```
## <date> <time> <name> <session label>
Done: <what works now, with the file paths>
In progress: <what is half done and where>
Next: <the next 1 to 3 tasks>
Decisions: <anything decided that others must know>
Blocked on: <person or file, with a deadline>
Contracts touched: <none, or which and the commit>
```

### 10.3 Start-of-session prompt (paste into a new Claude Code session)

```
I am <Dev|Ananya>. Read CLAUDE.md, then docs/TEAM_README.md sections 2, 3 and 8, then my progress log docs/progress/<name>.md and the files in docs/inbox/<name>/. Summarise in 8 lines: what is done, what is in progress, what I should do next, and anything waiting on me. Do not change any file yet.
```

### 10.4 End-of-session prompt

```
Append a handoff entry to docs/progress/<name>.md using the template. Run the rule-checker subagent on the diff. Commit with a message in the form "<area>: <what>". Do not add any Claude or co-author line. Do not push; show me the git log and diff stats.
```

### 10.5 Resuming

`claude --resume` lists past sessions to continue, and `/rename` gives the current session a label. Use labels like `dev-sourcer` so sessions from different worktrees are easy to find. A resumed session still starts from the files, so still run the start-of-session prompt.

## 11. Both of us must understand every module

At the finals there is a live fix and a design question. Neither of us can say "the other person wrote that". Rules:

- By 6:15, each person gives the other a 10-minute walkthrough of their area: where the code is, how a case moves through it, what happens when it fails.
- Agents write most of the code, so read it. When an agent finishes a module, ask it to explain the data flow in 10 lines and check the explanation against the code.
- Keep modules small and names plain. If you cannot explain a function in two sentences, ask the agent to simplify it.

## 12. Windows and Linux differences

- **Line endings.** Dev adds `.gitattributes` with `* text=auto eol=lf` in the first commit. On WSL: `git config core.autocrlf input`. On native Windows: `git config core.autocrlf false`. Editors should save files with LF line endings.
- **Paths.** Use forward slashes in documents and code. Do not hard-code absolute paths.
- **File system.** In WSL keep the repo under `~`, not `/mnt/c`.
- **Executable bits.** Shell scripts need `chmod +x` on Linux. If a script is edited on native Windows, check `git diff` for mode changes.
- **Ports.** Server on 8000, web on 3000. If WSL cannot reach `localhost` from the Windows browser, use the WSL IP address or run the browser inside WSL.
- **Microphone for the voice demo.** Chrome on the demo laptop is what matters. Test the browser's speech recognition there before kickoff.

## 13. Kickoff plan (0:00 to 0:45)

Together (first 20 minutes):

1. Read the rulebook sections on deliverables and the repo. Ask the help-desk questions in section 15.
2. Dev creates the repo skeleton and pushes the first commit (section 7.2).
3. Both write `contracts/` (API routes, events, enums, owners).
4. Export `docs/context/`.

Then split:

| Dev | Ananya |
| --- | --- |
| Server skeleton, environment loading, model wrapper with cost log, Crustdata client, coverage test on 3 companies (one Indian and not a household name) | Next.js app skeleton, typed API client from `contracts/API.md`, ask screen shell, live-update client |
| Walking skeleton: question in, live Crustdata results out | Plan and panel view against the live API |

After 0:45 follow the schedule in the build guide, split between the two of us by the ownership table. The milestone is one full case running from question to cited memo by 5:15.

## 14. Before kickoff (no code)

- [ ] Both: Claude Code installed, logged in to Pro, `claude doctor` clean.
- [ ] Ananya: WSL 2 working, or the native fallback decided.
- [ ] Both: GitHub access to the organiser repo tested as soon as it is shared.
- [ ] Both: Mailpit installed (the default mail path). Gmail SMTP only if the help desk confirms it is a permitted API.
- [ ] Both: laptop, charger and college ID (rulebook section 1).
- [ ] Decide the allowlist: your two addresses plus any teammates.
- [ ] Both: $25 Claude API key available to the person who will put it in `.env`; neither of us exports it as `ANTHROPIC_API_KEY`.
- [ ] Both: Chrome with microphone permission tested on the demo laptop.
- [ ] Agree who answers as which expert persona during the demo (registered team members only).
- [ ] Copy these two files and the exported docs to a folder outside any repo, ready to paste in at 0:00.

## 15. Questions for the help desk at kickoff

1. Which APIs are permitted: Crustdata and the Claude API, and also web search and fetch, Gmail SMTP, and Chrome's built-in speech recognition (which, as far as we know, sends audio to Google)?
2. Is a development-time cache of real API responses allowed, if it is off for the finals run?
3. Is a teammate typing a persona's answer on the expert page acceptable, given rule 3.3 (teammates play counterparties) and rule 5.5 (no results entered by hand)?
4. May we add instruction files (`CLAUDE.md`, `.claude/`) prepared before kickoff, if the README says so? They contain no application code.

The rulebook already says AI coding tools are allowed (3.1) and that only registered team members may operate the service (5.1), so we do not ask whether judges may play experts. Do not ask about the unseen finals requests (rule 5.9).

## 16. Troubleshooting

| Problem | Fix |
| --- | --- |
| Claude Code asks about using an API key or shows API billing | An `ANTHROPIC_API_KEY` variable is set. Unset it in that shell, run `/logout` then `claude` and choose the subscription login. |
| Push rejected | `git pull --rebase origin main`, run tests, push again. Never `--force`. |
| `git rebase` shows conflicts in a file you do not own | Stop. Abort with `git rebase --abort`, message the owner, resolve together. |
| Everything shows as changed on Windows | Line endings. Check `.gitattributes` and your editor's LF setting. |
| `claude` not found after install | Add `~/.local/bin` to PATH: `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`. |
| WSL slow | The repo is under `/mnt/c`. Move it into the Linux home folder. |
| Agent edited the other person's file | Revert that file (`git checkout origin/main -- <file>`), tell the owner, and tighten the prompt with the ownership table. |
| Session hit the Pro limit | Commit and push, write the handoff entry, switch to documentation tasks, or wait for the reset. |

## 17. Sources

- Claude Code setup (Windows, WSL, native install): https://code.claude.com/docs/en/setup
- Using Claude Code with a Pro or Max plan (limits, API key trap): https://support.claude.com/en/articles/11145838
- Worktrees and parallel sessions: https://code.claude.com/docs/en/worktrees
- Subagents: https://code.claude.com/docs/en/subagents
- Agent teams: https://code.claude.com/docs/en/agent-teams
