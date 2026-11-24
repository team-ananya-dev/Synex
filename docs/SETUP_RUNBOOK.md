# Setup runbook: what a human must do

Claude Code agents cannot create accounts, receive keys, approve logins, or press buttons in a browser. This runbook lists everything only you can do, in order, with a check after each step. Anything not listed here, an agent can do.

Do part A tonight, part B at kickoff, part C once the first skeleton exists (about 0:45).

---

## Part A: before kickoff (no code)

### A1. Tools on both laptops

Run these and fix anything that fails.

```
git --version
node -v          # 20 or newer
python3 --version   # 3.10 or newer
claude --version
claude doctor
```

Ananya: do this inside the WSL 2 Ubuntu terminal. Install steps are in `docs/TEAM_README.md` section 4.

Check: all five print versions without errors, and `claude` opens with the Pro login (run `/status` inside it).

### A2. Make sure no API key leaks into Claude Code

In the shell you start `claude` from, run:

```
echo "${ANTHROPIC_API_KEY:-not set}"
```

It must print `not set`. If it prints a key, remove the line that sets it from `~/.bashrc`, `~/.profile` or the Windows environment variables, open a new terminal, and check again. If it is set, Claude Code can bill the API key instead of your subscription.

### A3. GitHub access

1. Make sure both of you have GitHub accounts.
2. Create an SSH key if you do not have one: `ssh-keygen -t ed25519 -C "<your email>"`. Press Enter through the prompts.
3. Print the public key with `cat ~/.ssh/id_ed25519.pub`, then add it at GitHub: Settings, SSH and GPG keys, New SSH key.
4. Test: `ssh -T git@github.com`. A greeting with your username means it works.

If the organisers use HTTPS or a token instead, do what they say at kickoff.

Check: `ssh -T git@github.com` greets you.

### A4. Claude API key for the app (the shared $25)

1. In the Anthropic Console, create an API key named `synex-hackathon` and fund or confirm the $25 balance. If the Console lets you set a spend limit, set it.
2. Save the key somewhere private (a password manager). Do not paste it into chat, a prompt, a document or a commit.
3. Look up the current model names and prices in the Console. Write them down; the app reads the model names from `.env`.
4. Test the key once, with the variable named `SYNEX_ANTHROPIC_KEY` (not `ANTHROPIC_API_KEY`):

```
export SYNEX_ANTHROPIC_KEY="<paste key>"
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $SYNEX_ANTHROPIC_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"<a model id from the console>","max_tokens":20,"messages":[{"role":"user","content":"Reply with the word ok"}]}'
unset SYNEX_ANTHROPIC_KEY
```

Check: the reply contains `ok`. Then close that terminal tab so the key is gone from the shell.

### A5. Crustdata key

The organisers give the Crustdata key at kickoff. Nothing to do tonight except read the Crustdata docs for the Person search and Company enrich endpoints, and write down the exact request shape for a past-employer search if the docs show one.

### A6. Mailpit (local inbox, the default mail path)

1. Download the Mailpit release for your operating system from its GitHub releases page and put the `mailpit` program somewhere on your PATH. Ananya installs the Linux version inside WSL.
2. Start it: `mailpit`.
3. Mailpit's usual defaults are SMTP on port 1025 and a web inbox at `http://localhost:8025`. Open that address in a browser.

Check: the inbox page loads (empty).

Gmail SMTP is an alternative only if the help desk confirms it is a permitted API. If it is, turn on 2-step verification for the sending Google account, create an app password, and keep it private. SMTP host `smtp.gmail.com`, port 587 with STARTTLS.

### A7. Decide the allowlist

Write the email addresses mail may go to: your two addresses, plus other registered team members if any. Only registered team members can play roles. Put them in a private note for kickoff; the code gets them from `.env`.

### A8. Chrome and voice

1. Install Chrome. On the demo laptop, open any page that offers browser speech-to-text and allow the microphone when asked. Speak and confirm that words appear.
2. Test your headphones or microphone. Use headphones during the demo to avoid echo.

Check: speech-to-text works in Chrome on the demo laptop.

### A9. Bring list

Laptop, charger, college ID (rulebook section 1). Phone charged for the hotspot backup network.

### A10. Print or save

Save the rulebook PDF on both laptops. Keep this pack (the zip) ready to unzip at 0:00.

---

## Part B: at kickoff (0:00 to 0:20)

Do these in order. Steps 1 to 3 are together.

1. **Confirm the team registration and the start time.** Both builders must be registered. Ask the help-desk questions from `docs/TEAM_README.md` section 15 (but never ask about the unseen finals requests).
2. **Get the organiser repo URL and the Crustdata key.** Do not share either with another team.
3. **Wait for the official start announcement.** No code before it. Agents may only read and plan until then.
4. **Dev clones:**

```
git clone git@github.com:team-ananya-dev/Synex.git
cd Synex
git remote -v
```

5. **Dev copies the pack into the repo root** (unzip so that `CLAUDE.md`, `docs/` and `.claude/` sit at the top), then exports the two documents to `docs/context/` (see `docs/context/README.md`).
6. **Dev makes the first commit and pushes:**

```
git add -A
git commit -m "docs: add team context and agent instructions"
git push origin main
git log -1
```

`git log -1` must show no Claude or co-author line.

7. **Disclose in the README later:** the instruction files were prepared before kickoff and contain no application code.
8. **Ananya clones** after Dev's push: same `git clone`, then `git config user.name "Ananya"` and `git config user.email "<her email>"`.
9. **Create `.env`.** After the skeleton exists, each person copies `.env.example` to `.env` and fills it in by hand: `SYNEX_ANTHROPIC_KEY`, the Crustdata key, the allowlist addresses, the mail settings. Never paste keys into a Claude prompt; the agent reads `.env` through the app, not through chat.
10. **Start Claude Code** in the repo and paste your kickoff prompt from `docs/KICKOFF_PROMPTS.md`.

Check: `git log --oneline` shows the first commit on both laptops, and `ls docs` shows the pack.

---

## Part C: wiring checks (about 0:45, then again at 2:30 and 5:15)

Once the first skeleton exists, you verify the chain end to end. Ask the agent to do each step and watch the result yourself.

| # | Check | You should see |
| --- | --- | --- |
| 1 | Server health: open `http://localhost:8000/health` | a short OK response |
| 2 | Web to server: load `http://localhost:3000` and trigger a call to the server | data on screen, no CORS error in the browser console (F12) |
| 3 | Server to Crustdata: run the coverage test on a test company | people returned and the credit counter goes up |
| 4 | Server to Claude: trigger one small model call | one new row in `llm_calls` with tokens and dollars |
| 5 | Live stream: start a case | events appear on the case page without reloading |
| 6 | Mail: approve a drafted email to an allowlisted address | it shows up in the Mailpit inbox |
| 7 | Allowlist: try to approve an email to a non-allowlisted address | the app refuses and the audit trail records the refusal |

Common fixes:

| Symptom | Fix |
| --- | --- |
| CORS error | The agent adds the web origin to the server's allowed origins, or proxies server calls through the web app. |
| Port already in use | Close the old process or change the port in `.env`. |
| Windows browser cannot reach WSL `localhost` | Use the WSL IP address, or run the browser inside WSL. |
| Crustdata returns 401 or 403 | Check the key, the `Authorization: Bearer` header and the `x-api-version` header. |
| Model call rejected | The model name in `.env` is wrong, or the key has no balance. |
| Nothing arrives in Mailpit | Check the SMTP host and port in `.env` and that `mailpit` is running. |

---

## What an agent can do for you here

Once you have the keys in `.env`, an agent can write the server and web skeleton, the Crustdata client, the model wrapper, the mail sender, the health and wiring tests, and the `.gitignore`. It cannot create accounts, fund the key, approve logins or press the approve button in the browser.


## Keys: local clone or hosted site

- **Run it locally.** Copy `.env.example` to `.env` and fill in `SYNEX_ANTHROPIC_KEY` and `CRUSTDATA_API_KEY` with your own keys. The server uses them and the Ask page does not ask for any key. A key missing from `.env` is asked for on the Ask page instead.
- **Host it (for example on Render).** Do not set either key on the server. Each visitor enters their own two keys on the Ask page, after the landing page. The keys stay in that browser tab, travel as `X-Anthropic-Key` and `X-Crustdata-Key` headers, and are held in server memory per case. They are never stored. After a server restart a visitor enters them again.
- **Taking an old shared key offline.** Delete `SYNEX_ANTHROPIC_KEY` and `CRUSTDATA_API_KEY` from the host's environment, then revoke them in the Anthropic Console and the Crustdata dashboard. Deleting from the host alone does not invalidate a key.
