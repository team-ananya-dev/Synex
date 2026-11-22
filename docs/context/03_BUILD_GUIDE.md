NOTE (Synex repo): the roles table and schedule below assume four people. We are two (Dev and Ananya); the two-person split is in docs/TEAM_README.md. Everything else applies as written.

Synex: Developer Build Guide (7-hour)
Nov 22, 2026 - @Dev
What we are building
Synex answers one business question with a cited memo built from several former employees' answers, and every step runs live inside the 7-hour build.
A customer types a question such as "How is quick-commerce unit economics trending at Zepto?". Synex then does six things:
1.  Splits the question into sub-questions and decides what expertise it needs.
2.  Finds former employees through Crustdata's people data and ranks them.
3.  Screens the question and each person with fixed compliance rules.
4.  Drafts the outreach and puts it in an approval queue; a teammate approves, and mail goes only to teammate addresses.
5.  Collects answers through a web form or a free browser voice interview, then screens each answer.
6.  Writes a memo where every claim cites an accepted answer or a Crustdata record, with an audit trail and a cost log.
What must work at hour 7
• One full case, start to finish, on a question we have not rehearsed.
• At least two teammates answering as experts, one by form and one by voice.
• A memo that shows agreement, disagreement and a confidence level per sub-question.
• A visible refusal when the voice agent is asked for confidential information.
• Nothing pre-loaded: all results come from live calls made during the run.
Rulebook limits that shape the build
Seven rules from the Participant Rulebook decide what we may build and how we must demo it.
Rule
What it means for us
7-hour build, no pre-written code
Today we only plan: decisions, sketches, written notes. No schemas, scaffolds or prompt files before kickoff.
Agents never contact real people
Outreach goes only to a hard-coded allowlist of teammate emails, enforced in code. Teammates play the experts.
Irreversible actions need human approval
Every email and every payment goes through an approval queue with an approve click.
No stored results, no mocks shown as live
Nothing pre-cached for the demo. A dev-time cache of real API responses is for building only; confirm with the help desk.
No hand-entered results
Case data, expert answers and the memo all come from the running system.
Unseen requests at finals
The pipeline must be general. No Zepto-only logic anywhere.
Live fix and design question
Keep the code small and every teammate fluent in every module. Rotate the walkthrough.
The README must also credit every open-source library and state plainly what is simulated (the payment ledger) and what is real.
Architecture and tech choices
One FastAPI server runs every stage, calls every outside service and writes every event to one SQLite file.
The browser reads progress over one server-sent-events stream per case. The stage runner calls Crustdata and Claude through wrapper functions that log each call, and mail can leave only through the action gate.
Choice
Why
Next.js, Tailwind, shadcn/ui
Seven screens in a few hours; tables, dialogs and badges come ready-made.
FastAPI in Python
Background tasks and streaming in one small process, with a Python client for the Claude API.
SQLite
One file, no service to start, and a judge can be shown any table live.
Server-sent events, not WebSockets
Updates only flow server to browser, so the simpler tool is enough.
Claude with JSON-schema replies
Code reads fields, never parses prose.
Chrome speech APIs
Free, no account, no key.
Mailpit (local inbox)
A local inbox that stays inside our environment; Gmail only if it is a permitted API.
Keep one repo with two folders, one for the server and one for the web app, and commit small pieces often so the history shows the build.
Data model and case states
Eleven SQLite tables hold everything; each case moves through eight states, and every change of state writes an audit event.
Table
Holds
Key columns
cases
One customer question
id, question, state, budget_cap, created_at
subquestions
The plan the decomposer produced
case_id, text, expertise_needed, target_companies
candidates
People found by sourcing
case_id, crustdata_ref, name, last_company, role, exit_date, rank_score, screen_status
screen_results
One row per rule per candidate
candidate_id, rule, passed, reason
outreach
Drafted emails and form links
candidate_id, channel, body, status (drafted, approved, sent), approved_by
responses
Raw expert answers
candidate_id, subquestion_id, mode (form, voice, text), text, received_at
response_screens
Verdict per response
response_id, verdict (accepted, redacted, held, rejected), reason
findings
Claims in the memo
case_id, claim, confidence, sources (response ids or Crustdata refs)
ledger
Simulated holds and payouts
case_id, kind (hold, capture, payout), amount, approved_by
events
Append-only audit trail
case_id, ts, actor, action, payload, prev_hash, hash
A separate llm_calls table logs model, tokens in and out, cost and purpose for every model call.
Case states, in order
1.  DRAFT: question typed, not yet planned.
2.  PLANNED: sub-questions and expertise needs produced.
3.  SOURCING: Crustdata search and people screen running.
4.  AWAITING_APPROVAL: shortlist and drafts wait for a teammate's click.
5.  COLLECTING: links are out; answers arrive.
6.  SYNTHESIZING: screened answers go into the memo writer.
7.  DELIVERED: memo is shown with its audit trail.
8.  REFUSED or FAILED: the question failed the screen, or too few accepted answers came back to support any claim.
The audit trail chains each event to the previous one by hash, so tampering is detectable. A short function that recomputes the chain is enough for the demo.
Pipeline and job design
Eight stages run as background jobs in one FastAPI process, and each stage writes its result to the database and emits an event the browser receives live.
#
Stage
Input
Output
Model
1
Question screen
Question text
Allowed, refused or rewritten
small
2
Decomposer
Question
3 to 5 sub-questions, expertise needed, target companies
small
3
Sourcer
Target companies, roles
Candidate list from Crustdata
none
4
People screen
Candidates
Pass or fail per rule, with reasons
none (plain code)
5
Ranker
Passed candidates, sub-questions
Score and one-line reason each
small
6
Outreach writer
Shortlist, sub-questions
Email draft and form link per expert, in the approval queue
small
7
Response screen
Each incoming answer
Accepted, redacted, held or rejected
small
8
Memo writer
Accepted answers, Crustdata company data
Cited memo with confidence per sub-question
large
Job mechanics
• Use a plain in-process task runner (FastAPI background tasks or asyncio). No queue service.
• Each stage is a function that takes a case id, reads its input from the database, writes its output, then appends an event. A crashed stage can be re-run safely.
• Stages 3 and 4 run as soon as stage 2 finishes. Stages 7 and 8 run whenever a new answer arrives, so the memo updates as answers come in.
• The browser listens on one server-sent-events stream per case. Event types: stage_started, stage_done, candidate_added, approval_needed, response_received, memo_updated, cost_updated.
• Stage 4 is rules in code, not a model call, so a judge can read why a person was excluded.
Crustdata: what to test first and what to do when it fails
The whole product rests on Crustdata's people search, so the first 45 minutes answer five questions before any other feature gets built.
We use the 15,000 API credits across Company identify and enrich, Person search and enrich. Requests carry an Authorization: Bearer header and x-api-version: 2025-11-01. Confirm both against the docs on the day.
Coverage test (run on 3 companies, one of them Indian and not a household name)
Question
If yes
If no
Can person search filter by a past employer?
Use it directly
Search by company and title, then filter on each profile's job history in code
Does a profile show when someone left a company?
Apply the 6-month cooling-off and 24-month freshness rules
Treat the rule as unknown and mark the candidate "exit date unverified"
Does it return a work email?
Not needed: outreach goes to teammates only
Same. Never contact the real person.
What does one search and one enrich cost in credits?
Log it per call and set a per-case cap
Assume the higher cost and cap lower
Is the data live or indexed?
State this accurately in the README
Same
Rules for using it
• Every Crustdata record the memo cites is stored with its call id, so a judge can click through to the raw response.
• Add a per-case credit cap and a visible counter in the UI. Stop sourcing when it is hit.
• If a company returns fewer than 3 usable candidates, the case says so and shows what was missing. It does not fill the gap with invented people.
• Company data (headcount trend, funding) is used to cross-check what experts say. Disagreements are shown in the memo, not hidden.
• Ask the help desk whether web search and fetch count as permitted APIs, since they would widen coverage.
LLM layer and the $25 budget
Use the small model for seven of the eight stages and the large model only for the memo, and log the cost of every call.
Model split
• Small model: question screen, decomposer, ranker, outreach writer, response screen, and the voice interviewer's turns.
• Large model: the memo writer, once per synthesis run.
• I don't have today's per-token prices. Read them from the Anthropic console at kickoff and set the cost function from those numbers.
How every call is made
• One wrapper function does all model calls. It takes a purpose label, a prompt and a JSON schema, validates the reply against the schema, retries once on invalid output, and writes a row to llm_calls.
• Replies are structured JSON, never free text that code has to parse.
• Every claim the memo writer returns must carry source ids. A checker in plain code drops any claim whose ids do not exist in the database (cite or drop).
• Prompts are written in the first hour as notes in words, then become code after kickoff.
Budget rules
• Cap each case at a fixed dollar amount in code. The UI shows spend so far.
• Cache model replies by a hash of purpose and input during development only. Turn the cache off for the finals run so every result is live.
• Never call the large model while debugging the pipeline. Test the memo writer on small inputs.
• Keep about $5 unspent as a reserve for the finals demo and the unseen request.
Schemas to define first (names only today)
• plan: list of sub-questions with expertise needed and target companies.
• rank: candidate id, score, one-line reason.
• screen_verdict: verdict, reason, redacted text if any.
• memo: list of findings, each with claim, confidence, source ids, and an agreement label (consensus, split, single source).
Compliance, approval queue and payments
Compliance is plain code with stated reasons, and every irreversible action waits in one approval queue.
People screen (stage 4), one function per rule
Rule
Pass condition
Not a current employee
Profile shows an end date at the target company
Cooling-off
Left at least 6 months ago
Freshness
Left no more than 24 months ago
Competitor conflict
Current employer is not a direct competitor of the client's named company
Restricted list
Not on a small hard-coded restricted list
Sensitive role
Flagged for review if the role was legal, finance control or security
Do-not-contact
Not in the do-not-contact table
Each rule returns pass or fail plus a one-line reason, stored in screen_results. A failed rule removes the person from the shortlist and the reason is shown to the customer.
Question screen and response screen
• The question screen refuses requests for non-public information about a named company. The refusal and its reason are shown, not hidden.
• The response screen labels each answer accepted, redacted, held or rejected. It looks for confidential figures, named internal documents and anything the expert says is under NDA.
• If fewer than 3 accepted experts share a role label, coarsen the label in the memo (for example, "former senior operations leader").
Approval queue (the rule that keeps us legal)
• The agent can only create a drafted action. It cannot send one. A teammate presses approve in the UI, which records who approved and when.
• Email send is one function that refuses any address not on the hard-coded teammate allowlist. Test this with a deliberate non-teammate address and show the refusal.
• Send through Mailpit, a local inbox. Use Gmail SMTP only if the help desk confirms it is a permitted API.
Payments
• A ledger table records an authorised hold when the plan is approved, a capture per answered sub-question, and an expert payout per accepted response.
• It is simulated. The UI and README say "simulated ledger". No payment provider is called.
• Payout appears in the approval queue like an email, so a person clicks to release it.
Expert page and free voice interviewer
The expert page is one unauthenticated page per link token with two modes, and the voice mode runs entirely in the browser at no cost.
Expert page
• The email contains a link with a random token. The page shows the sub-questions that expert was matched to, the rules (no confidential information, answers are screened), and the payment terms labelled simulated.
• Mode A, form: one text box per sub-question, a submit button, nothing else. This is the reliable path.
• Mode B, voice: a start button opens the interview described below.
• Submitting writes to responses and triggers stage 7 for that answer.
Voice interviewer, built from free parts
1.  Chrome's SpeechRecognition turns the expert's speech into text. It works only in Chrome and needs microphone permission, so test on the demo laptop's actual browser. As far as I know it sends audio to Google's servers, so ask the help desk whether that is a permitted API.
2.  The browser sends each utterance to the server with the interview state.
3.  The small model returns the next question, a follow-up or a wrap-up, plus a flag saying whether the expert just tried to ask us for something confidential.
4.  The browser speaks the reply with speechSynthesis. The voice sounds robotic and that is acceptable.
5.  The server stores the full transcript as a response with mode = voice.
Interviewer rules
• Ask the sub-questions one at a time and probe at most twice per sub-question.
• If the expert asks the agent to reveal what other experts said, who the client is, or any other confidential detail, the agent refuses out loud and logs a refusal event. This is the behaviour the rulebook tests.
• Never claim to be a human.
Fallbacks
• If speech recognition fails, switch the same page to typed chat with the same agent and label the response mode as text.
• Free open-source options (faster-whisper for speech to text, Piper for speech to speech) sound better but take real setup time. Try them only if the browser route is done by hour 5, and credit them in the README.
Response screening
Each submitted answer is judged on its own: accepted goes into synthesis, redacted goes in with the flagged span removed, held waits for a teammate, rejected is excluded with the reason logged. The customer sees the counts, not the rejected text.
Synthesis, screens, audit trail and cost log
The memo is what wins the demo, so synthesis rules are written in code and shown on screen rather than left to the model's judgment.
Synthesis rules
• Group accepted answers by sub-question.
• Count independent sources only. Two experts who worked at the same company, in the same function and city, with at least 3 months overlap, count as one source.
• Label each finding: consensus (2 or more independent sources agree), split (they disagree, both views shown), single source (one independent source, shown but marked weaker).
• Confidence is High with 3 or more independent agreeing sources, Medium with 2, Low with 1. Compute it in code and pass it to the model, which only writes the wording.
• Compare each finding against Crustdata company data where a comparison is possible (for example headcount trend). Show "agrees", "conflicts" or "no data".
• Cite or drop: a claim without valid source ids is removed before the memo is shown. If a sub-question has no accepted answer, the memo says so.
Screens, in the order a demo walks through them
1.  Ask: question box, optional budget cap.
2.  Plan and panel: sub-questions, ranked candidates, and who was excluded with reasons.
3.  Approval queue: drafted emails and payments, each with an approve button and the allowlist check shown.
4.  Live case page: stage progress, answers arriving, the memo filling in, credit and dollar counters.
5.  Memo: findings with confidence, agreement label, cited sources and the company-data check.
6.  Audit trail: the event list with the hash chain check, plus the cost log by model call.
7.  Expert page: form and voice (see above).
Skip login, signup, profiles, document upload and reviewer portals.
Audit trail and cost log
• Every state change, approval, refusal, screen verdict and model call appends one event with actor, action and payload.
• Each event stores the previous event's hash and its own, so a verify button can recompute the chain.
• The cost log shows each model call with tokens and dollars, and each Crustdata call with credits.
Team split, schedule and cut lines
The plan assumes four people and ends with a committed repo, README, architecture diagram and demo video at hour 7.
Voice and the audit screens start only after one full case runs, and README work starts no later than 6:15.
Roles (with three people, merge role B into A)
Role
Owns
Hands off to others
A: pipeline
Database, job runner, Crustdata client, sourcer, ranker, live-update stream
Candidate and response rows for everyone
B: compliance and actions
People screen, question screen, approval queue, email allowlist, simulated ledger, audit hash chain
Approved actions and screen verdicts
C: customer interface
Ask, panel, approval, live case, memo and audit screens
Needs A's event stream by hour 2
D: expert side and synthesis
Expert page, voice interviewer, response screen, memo writer and checker
Needs B's screen rules by hour 4
Cut lines if behind (cut in this order)
1.  Free open-source voice models. Stay on the browser voice.
2.  The company-data cross-check in the memo.
3.  The audit hash-chain verify button. Keep the plain event list.
4.  Voice mode entirely. Ship form mode and typed chat, labelled honestly.
Never cut: the approval queue, the email allowlist, the response screen, cite-or-drop, or the README and demo video.
Risks
Risk
Early sign
Response
Crustdata lacks past-employer data for Indian companies
Coverage test at 0:45 returns fewer than 3 usable people
Search by company and title, filter job history in code, say so in the README
Memo quality is weak
Claims repeat or lack sources at 4:30
Tighten the schema, pass confidence from code, shorten the memo
Voice recognition fails on the demo laptop
Recognition errors in the first test
Switch the page to typed chat for that expert
Model spend runs high
Counter passes $15
Disable the large model outside the final run
A teammate cannot explain a module
Live fix question at finals
Each person walks the others through their module before 6:15
Before kickoff (no code)
[ ] Assign the four roles and each person's module walkthrough.
[ ] Read the Crustdata docs and write the five coverage questions on paper.
[ ] Check the demo laptop's Chrome microphone and speech recognition.
[ ] Install Mailpit (a local inbox) and decide the teammate allowlist addresses. Use Gmail only if the help desk confirms it is a permitted API.
[ ] Confirm the $25 Anthropic key works and note the current model prices.
[ ] Write the help-desk questions: which APIs are permitted (web search and fetch, Gmail SMTP, Chrome speech recognition), is a dev-time cache allowed, and is a teammate typing a persona's answer acceptable.
Final deliverables checklist
[ ] Code committed throughout in the organizer repo, nothing rewritten.
[ ] README that states what is real and what is simulated, with open-source credits.
[ ] Architecture diagram.
[ ] Demo video recorded from a real run.
[ ] Finals run on an unseen question, live, with the cache off.