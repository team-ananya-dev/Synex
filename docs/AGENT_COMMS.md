# How agents and people stay in sync

Three layers, from simple to optional. The first two are all we need. The third is a place to stop and think before adding tools.

| Layer | Who talks to whom | How | Needs setup? |
| --- | --- | --- | --- |
| 1. Same laptop | Your own Claude Code sessions | Claude Code cross-session messaging | No, if the version is new enough |
| 2. Between you and Ananya | Dev's agents and Ananya's agents | The git repo: progress logs, inbox, contracts, decisions | No |
| 3. Optional | Anything else | A chat app between the two humans | A group chat |

## 1. Several sessions on one laptop

Claude Code can pass messages between your own sessions on the same machine. Claude finds the target with a listing tool and sends a plain-text message; you never call these tools yourself. On the same machine the message travels over a local socket and does not go through Anthropic's servers.

Requirements:

- Claude Code v2.1.224 or later on Linux, macOS and WSL 2. On native Windows, v2.1.234 or later.
- Both sessions run on the same machine. A WSL 2 session and a native Windows session on one computer cannot reach each other, so Ananya should run all her sessions inside WSL 2, not mix the two.
- Check with `claude --version`. Inside a session, `/list-agents` (or `/peers`) lists the sessions Claude can reach. If that command is not recognised, the version is too old.

How to use it:

1. Give each session a name when you start it: `claude --name dev-sourcer`, or run `/rename dev-sourcer` inside it. Use short names with no spaces.
2. Tell Claude what the other session needs to know. Examples:
   - `Let @dev-actions know the contract for the approval queue changed; the new field is approved_by.`
   - `Ask @dev-sourcer whether the candidate rows have exit_date yet.`
3. Type `@` and the first letters of a session's name to pick it from a list.
4. Claude on the receiving side sees the message between its tool calls, or starts a new turn if idle. Press Ctrl+O in a session to read a received message in full.

Rules of thumb:

- A message is text only. It carries no files and no history. Put anything long in a file (`docs/inbox/...` or a progress entry) and send the path.
- A message never counts as approval. The receiving session still asks you for any permission it needs, and it will not change settings or `CLAUDE.md` because a message asked.
- Do not ask another session to do something your own session was blocked from doing.
- By default, a session that skips permission prompts holds messages from other sessions for your approval, and the reverse. If messages seem to vanish, check whether one of the sessions was started in a mode that bypasses permissions. We do not use that mode, so the default works.
- Repeated identical messages are throttled, so message loops stop on their own. Keep messages short and send each once.
- Worktree sessions (see `docs/TEAM_README.md` section 7.4) are exactly the case this was built for: "I merged the contracts change, rebase on main."

## 2. Between Dev's agents and Ananya's agents

Claude Code's documentation describes messaging only between your own sessions, including ones on your other machines or in the cloud, reached through your own signed-in account (Remote Control). Dev and Ananya have separate accounts, so I expect Dev's sessions cannot reach Ananya's. Do not plan on it. There is no built-in channel between the two of you, and we do not need one.

The channel is the git repository. Each agent reads what the other person's agents wrote, through files that cannot conflict:

| File or folder | Written by | Read by | Purpose |
| --- | --- | --- | --- |
| `docs/progress/dev.md`, `docs/progress/ananya.md` | its owner, append only | everyone | What is done, in progress, next, blocked |
| `docs/inbox/<name>/` | anyone, new files only | `<name>` | A request for a change in `<name>`'s area |
| `contracts/*.md` | both, append only | everyone | API shapes, events, enums, ownership |
| `contracts/decisions/<date>-<who>-<topic>.md` | anyone, one new file per decision | everyone | A decision others must know, with a reason |
| Git history | everyone | everyone | What actually changed and when |

Routine that keeps both sides current:

1. **Start of every task:** run `/sync` (below). It fetches `origin`, summarises what changed since your last pull, reads the other person's newest progress entry and any new inbox or contract files, and flags anything that could conflict with your branch. It changes nothing.
2. **Before every push:** run `/sync` again, then rebase as in the team README.
3. **Every 30 to 45 minutes:** push, even if the work is small, so the other person's `/sync` sees it.
4. **End of every session:** run `/handoff` to append a progress entry.
5. **A contract change:** write the decision file, push it straight away, then send the other person a chat message (layer 3) naming the file. An agent on the other side will find it on its next `/sync`; the chat message is the nudge.

How an agent knows what the other person's agents are doing: it does not watch them. It reads the repo. Whatever has not been pushed is invisible. That is why pushing often is a rule, not a courtesy.

### Custom commands

The pack includes `.claude/commands/sync.md` and `.claude/commands/handoff.md`. Typing `/` in a session should list them. If they do not appear, check the Claude Code documentation for the current location of custom commands, or paste the file's text as a prompt.

## 3. A chat between the two humans

Keep one group chat (WhatsApp, Telegram or anything you both read) for the two of you. Use short, fixed formats so the other person knows what to do:

- `PUSHED: <area> <short sha> <one line>` after a push the other side depends on.
- `CONTRACT: <file> <what changed>` after a contract or decision file.
- `BLOCKED: <what> <on whom> <by when>` when you cannot continue.
- `NEED: <inbox file>` when you left a request.
- `LIMIT: <name> hit a Claude limit, back at <time>` when a Pro limit blocks you.

Do not paste keys, `.env` contents, or the other team's anything into the chat.

Agents do not read the chat. If a message matters to an agent, it also belongs in a file.

## 4. Do we need Hermes or another communication layer?

No. Reasons, as far as I can tell from the Hermes documentation I read (I have not run it):

- Hermes Agent is an open-source agent framework from Nous Research. It is its own agent runtime, not a plug-in for Claude Code. It has a messaging gateway (Telegram, Discord, Slack, WhatsApp and others) and a plug-in for agent-to-agent calls between Hermes agents on different machines.
- Our agents are Claude Code sessions, not Hermes agents. To use Hermes' agent-to-agent layer, both of you would run Hermes agents instead of or alongside Claude Code, set up its gateway and plug-ins, and give it a model provider. If it used our Claude API key, it would spend the $25 meant for the product.
- The agent-to-agent piece appears to be a separate plug-in, and the other plug-in that adds conversational relays between agents is third-party. That is more moving parts than a seven-hour build can carry.
- Rule 12 of the rulebook says open-source code must be credited in the README, and rule 5 says agents may use only permitted APIs. A new agent framework adds both questions.
- The problem we have is small: two people, each with a few agents, one repo. Files and git solve it without a server, a key or a gateway.

When a communication layer would be worth it: more than two people, agents that need to act while no human is at the keyboard, or work that must hand tasks to each other in seconds. None applies here.

If you still want a live channel between laptops later, Claude Code has a feature called Channels that pushes external events (for example chat messages) into a session. I have not tested it. Treat it as an experiment after the 5:15 milestone, not part of the plan.

## 5. Quick reference

| I want to | Do |
| --- | --- |
| Tell my other session something | Name sessions, then `Let @name know ...` |
| See which sessions I can reach | `/list-agents` |
| Catch up on Ananya's (or Dev's) work | `/sync` |
| Ask the other person to change something | New file in `docs/inbox/<name>/`, then a chat nudge |
| Record a decision | New file in `contracts/decisions/` |
| Hand off my session | `/handoff` |
| Know why messages were not delivered | Check versions, then whether a session bypasses permissions |
