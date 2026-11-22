NOTE (Synex repo): this is the full product design. Only the "Hackathon scope" section decides what we build in the 7 hours; everything else is the reference for how it should behave.

Synex: Full Site Flow and Rules
Nov 21, 2026 · @Dev
Overview
Synex is a two-sided site: customers ask a research question, we collect compliant answers from many former employees at once, and we return one cited synthesis. Customers are funds, PE firms, consultants and in-house strategy teams. Experts are people who used to work at the company in question.
The flow in one line: question, research plan, compliant expert panel, invites, responses by form, doc or AI call, response screening, live synthesis, delivered memo with audit trail.
Five rules never bend:
1.  Screen people first. Nobody is contacted until they pass the compliance screen.
2.  Screen responses second. No response reaches a customer until it passes the response screen.
3.  Keep experts anonymous. Customers see role, tenure range and region. They never see a name or contact detail, and all contact goes through us.
4.  Cite everything, log everything. Every claim in a memo links to a response, a Crustdata record or a web page, and every step lands in the audit trail.
5.  Experts opt in and get paid. Consent comes before any question, experts can stop at any time, and accepted responses are paid.
Pricing principle: customers pay for answered sub-questions, not for lists of contacts.
Actors and roles
Five kinds of actor use the site, and the line between what each can and cannot do is what keeps it compliant.
Actor
Who they are
Can do
Cannot do
Customer
Analyst or research lead at a fund, PE firm or consultancy
Ask questions, approve the plan, set panel size and budget, remove panel members, read responses and memo, export
See expert names or contact details, contact experts directly, edit responses
Customer admin
Compliance officer or team lead at the customer
Set the restricted list, cooling-off and blackout windows, approve flagged experts, read the audit trail
Change a response or a screening result
Expert
Former employee of the target company or a peer company
Accept or decline, choose a response mode, answer, redact before submitting, withdraw, get paid, delete their data
See the customer's name or the full question set
Synex reviewer
Our staff
Review held responses and flagged experts, handle disputes and refunds, manage the do-not-contact list
Edit expert answers (they can only accept, redact or reject)
System agents
Software
Decompose the question, source experts, screen, rank, write outreach and forms, interview, synthesise
Send anything to a customer without passing the screens
Customer journey
A customer goes from a typed question to a delivered memo in ten steps, and money is only authorised at step 4 and only captured at step 9.
1.  Sign up. Work email required, with the organisation checked by email domain. The customer accepts the terms: research use only, no material non-public information, no attempts to identify experts.
2.  Set up the workspace (once). The customer or their admin enters the restricted list (companies and people), cooling-off period (default 6 months), freshness window (default 24 months), earnings blackout windows for listed companies, default budget cap, and who may approve flagged experts. These settings apply to every case.
3.  Ask. One text box plus a target company. Optional fields: panel size (default 20 invited), budget cap, deadline (default 72 hours), geography and language. The question is screened first (see Compliance rules): questions that ask for non-public information are rejected with a reason or rewritten.
4.  Review and approve the research plan. The site shows 3 to 5 sub-questions, the roles that would know each answer, and a coverage target: every sub-question answered by at least 2 independent experts. The customer can edit or delete sub-questions and adjust target roles. Approving authorises a payment hold equal to the maximum charge (see Pricing).
5.  Panel build, live. The candidate pool streams in as anonymised cards: role, company, tenure range, region, exit date range. Each card carries a pass or reject badge with the exact rule. Rejected cards stay visible but greyed out. Flagged cards wait for the customer admin. The top 20 or so become the invited panel, and the customer can remove anyone but cannot add by name.
6.  Outreach. The customer sees the invite template and can edit the neutral topic wording within limits (no customer name, no company non-public details). Invites go out once. Reminders go at 24 and 48 hours. If coverage is lagging and budget allows, the system tops up from the next-ranked candidates.
7.  Live case page. A panel status board shows invited, opened, consented, in progress, submitted, screened, accepted, declined and no reply. A coverage meter per sub-question shows accepted answers against the target of 2. Accepted responses appear as anonymised cards. The synthesis and confidence update as each one lands.
8.  Read the memo. Verdict and confidence, then a section per sub-question: consensus or disagreement, numeric ranges, best quotes, what the Crustdata company data says, single-source flags, gaps and suggested next questions.
9.  Close and pay. The case closes when every sub-question is covered or the deadline passes. The customer is charged for answered sub-questions only, and the rest of the hold is released. The memo and audit trail export as a PDF or doc.
10.  Afterwards. The customer rates quality, can reopen the case with a new question, and can reuse the panel only for experts who agreed to be recontacted.
Expert journey
An expert can finish in about ten minutes from a phone, with no account, and gets paid only for accepted responses.
1.  The invite. An email with a neutral subject. It says who we are, the topic in neutral terms, the payout, the time each mode takes, and how we found them (their public professional profile). It does not name the customer, and it includes an opt-out link and a privacy notice.
2.  The landing page. A private link with no password. It shows the topic, the payout and three ground rules: do not share anything confidential, nothing covered by an NDA, and nothing non-public about the company's finances. The expert ticks four attestations: not currently employed by the company, left on the date shown, not bound by confidentiality that blocks this topic, and will not share confidential or non-public information. Buttons: accept, decline, never contact me again.
3.  Choose a mode. Form (about 10 minutes, autosaves, works on mobile). Doc (write freely or fill a template, own words only, no company documents). AI call (15 to 20 minutes, start now or schedule, with a compliance script at the start). They can switch mode before submitting.
4.  Respond. Forms are generated from the sub-questions: numeric ranges, scales and short free text. Every question has an option to say "I can't answer without sharing confidential information" or "I don't know", and a confidence self-rating. In an AI call the agent follows the same guide, asks follow-ups, and stops and redirects if the expert drifts into confidential detail.
5.  Review and submit. The expert sees exactly what the customer will see (anonymised), can redact lines, and re-confirms the attestation. They can withdraw before submitting.
6.  Screening. The response screen returns one of four results: accepted, accepted with redactions, held for human review, or rejected. The expert is told which and why.
7.  Payout. Paid per accepted response at the rate on the landing page. Responses rejected for confidentiality are not paid, and the expert is told this before starting. Held responses are paid or not once a reviewer decides.
8.  Afterwards. Experts can optionally create a profile to set topics, rates, do-not-contact preferences and recontact consent. They can see what they shared (anonymised) and ask for deletion at any time.
Case lifecycle
A case only moves forward through seven states, except that the plan can loop back to Draft and the panel can be topped up while collecting.
State
Enters when
Leaves when
Money
Draft
Customer submits a question
Question passes the screen and a plan is generated
None
Plan review
Plan generated
Customer approves, or edits and regenerates
None
Funded
Plan approved
Hold placed successfully
Maximum charge authorised
Sourcing
Hold placed
Panel of about 20 passes the people screen, with flagged ones approved or dropped
Hold only
Outreach
Panel ready
Invites sent
Hold only
Collecting
Invites sent
Every sub-question answered, the deadline passes, or the customer closes it
Experts paid as responses are accepted
Closed
Collecting ends, or the case is cancelled
Final
Captured for answered sub-questions; the rest released
Compliance rules
Compliance runs at four points: on the question, on each person, on each response, and on what customers can see. The first two are plain rules in code. The response screen is partly LLM-based, so it is a first pass for a human reviewer, not a legal sign-off.
1. Question screen
A question is rejected or rewritten if it asks for non-public information. Examples: unreleased results, upcoming earnings, M&A talks, unannounced products, individual customers' contract terms. The customer sees the reason and a suggested rewrite (for example, ask about how the business model works, not what next quarter will show).
2. People screen
Each rule returns pass, fail or flag, with a reason string saved to the audit trail. Defaults are configurable per customer.
Rule
Logic
Example reason shown
Not a current employee
Current employer is not the target company
Still employed at the target
Cooling-off respected
Left at least 6 months ago
Left 2 months ago, under the 6-month cooling-off
Knowledge still fresh
Left within the last 24 months
Left 4 years ago, information likely stale
No conflicted current role
Not now at a direct competitor in a sensitive role, or at a listed partner
Now VP Ops at a direct competitor
Restricted list
Not on the customer's restricted people or company list
On the customer's restricted list
Sensitive former role
C-suite, board, legal, IR and finance-control roles are flagged for manual review
Former CFO, needs manual review
Closed period (listed targets)
No outreach inside the customer's configured pre-earnings blackout
Target reports in 9 days, inside the blackout
Regulated roles
Current government or regulator employees are excluded
Current public-sector role
Do-not-contact
Not on our global suppression list
Previously opted out
3. Response screen
Every response is checked before a customer sees it. Checks: non-public specifics (unreleased numbers, named customers' terms, internal documents, unannounced products), phrases that signal a leak ("I shouldn't say, but"), pasted company material, personal data about third parties, and mismatch with the expert's attestations.
Result
What happens
Accepted
Goes to the customer and the synthesis; expert paid
Accepted with redactions
Flagged lines removed, expert shown what was removed; expert paid
Held
Goes to a Synex reviewer; not shown to the customer until cleared
Rejected
Not shown; expert told why; not paid
4. Anonymity rule
Customers see role, tenure range and region, never a name or contact detail. If fewer than 3 candidates share a label such as "Former head of operations, Mumbai", the label is coarsened (region instead of city, wider tenure range) so one person cannot be picked out. Quotes are checked for identifying details before display.
Pricing, payments and refunds
Customers pay for answered sub-questions, so the refund guarantee is built in: the site authorises a maximum at approval and only captures money for what was answered. All figures below are placeholders to decide, not researched prices.
Definitions
• Answered sub-question: at least 2 accepted responses that address it, from independent experts (see Synthesis rules for how independence is judged).
• Single-source sub-question: 1 accepted response. It is delivered and clearly labelled.
• Maximum charge: price per answered sub-question times the number of sub-questions in the approved plan.
Money flow
1.  Plan approved: the customer's card or account is authorised for the maximum charge. Nothing is captured.
2.  Collection: we pay experts per accepted response out of our own cash, so cost risk sits with us.
3.  Close: the customer is charged for answered sub-questions, plus a reduced rate for single-source ones if we adopt that (decision needed). The unused hold is released.
Placeholder numbers
Item
Placeholder
Note
Price per answered sub-question
To decide
Should sit well under one expert-network call hour
Single-source rate
50 percent of full
Alternative: deliver free. Decision needed
Expert payout per accepted response
To decide
Scaled to mode and time (form, doc, call)
Default deadline
72 hours
One customer-requested extension
Refund and cancellation rules
Situation
Customer pays
Expert paid
Cancelled before outreach
Nothing; hold released
Nobody contacted
Cancelled after outreach
Answered sub-questions so far
Accepted responses
Deadline reached, coverage met
Full price for answered sub-questions
Accepted responses
Deadline reached, coverage partly met
Only answered (and single-source) sub-questions
Accepted responses
Deadline reached, no accepted responses
Nothing
Nobody
Customer disputes quality
A reviewer decides within 48 hours; credit or refund if the dispute holds
Unchanged
Response rejected by the screen
Not counted
Not paid
Experts are paid only after a response passes the screen, so a payout is never clawed back.
Synthesis and memo rules
The memo is built only from accepted responses, Crustdata records and fetched web pages, and it shows disagreement instead of averaging it away.
Sources and tags
• Every claim carries a tag: [R3] for accepted response 3, [CD] for a Crustdata data point, [Web] for a fetched page.
• Experts appear as E1, E2 and so on, with the anonymised label from the people screen.
• Cite or drop: a sentence with no valid tag is removed before the memo is shown.
Weighting
• Each response gets a weight from role match to the sub-question, how recently the expert left, seniority, and their own confidence rating.
• Weights are shown next to each response. They are never hidden.
Independence
• Two experts count as independent unless they worked at the same company, in the same function, in the same city, with at least 3 months of overlapping tenure. Correlated experts count as one source for the coverage test.
• This uses Crustdata work history only, so it is approximate. Say so in the memo footnote.
Agreement and disagreement
• Numeric answers show the range and the median, with the count behind them.
• Qualitative answers are grouped into claims. A claim is labelled consensus (two thirds or more of independent experts agree), split, or outlier (one expert against the rest).
• A claim with one source is flagged as single-source.
Confidence per sub-question
A word, not a false-precision number, plus the reason in one line.
Level
Default test
High
At least 3 independent accepted responses, consensus, and consistent with the company data
Medium
2 independent responses that agree, or 3 or more that are split
Low
Single source, or the experts contradict the company data
These thresholds are defaults to tune once real responses arrive.
Company-data check. Before any call, Crustdata company data gives a baseline: headcount trend, funding and hiring signals. Each sub-question shows whether the experts agree with it. A disagreement is surfaced, not smoothed.
Verdict language. The memo says what the evidence supports and what would change the view. It gives no price targets or buy and sell advice.
Quotes. Short, anonymised, and screened again for identifying detail. Paraphrase is the default.
Live updates. The memo has a version number. Each accepted response creates a new version with a short "what changed" note.
Audit trail, admin tools and privacy
Every decision in a case is logged in an append-only trail that a customer's compliance team can read and export. Each record stores the hash of the one before it, so tampering is detectable.
What the audit trail records
• The question, the screen result on it, and the approved plan with edits.
• Every candidate found, every rule result with its reason, and every manual approval with who made it.
• Every invite sent, opened, accepted, declined or ignored.
• Every response mode used, every screen result, and every redaction (what was removed and why).
• Every refusal by the AI interviewer.
• Every memo version, and every payment hold, capture, release and payout.
Admin tools (Synex reviewers)
• A review queue for flagged experts and held responses.
• A case list with status, spend and coverage.
• Refund and dispute handling.
• A global do-not-contact list, honoured within 24 hours of any opt-out.
• Default settings for rules, with changes logged.
Privacy rules
• Expert contact details are stored encrypted and never shown to customers.
• We keep only what a case needs. Experts can ask for deletion at any time, and we delete their responses and contact data except what the law requires us to keep.
• Invites go only to people reached through their public professional profile, and every invite includes how we found them and how to opt out.
• Crustdata's terms on storing and using people data must be checked before launch.
• Outreach and storage must be reviewed against India's DPDP Act, and the GDPR where experts are in the EU. This needs a lawyer before real use. It is not decided here.
Data model
Fourteen entities cover the whole site, and the case, the candidate and the response are the three that everything else hangs off.
Entity
Key fields
Notes
Organisation
name, email domain, settings
Holds restricted list, cooling-off, freshness, blackout windows
User
org, role (customer, admin)
Customers and customer admins
Case
org, question, target company, status, deadline, budget cap, panel size
Status follows the lifecycle below
SubQuestion
case, text, target roles, coverage target
3 to 5 per case
Candidate
case, Crustdata person ID, role, company, start and end dates, region
A snapshot of the profile at the time of the case
ComplianceResult
candidate, rule, result, reason
One row per rule per candidate
PanelMember
case, candidate, status, chosen mode
Status: invited, opened, consented, in progress, submitted, declined, no reply
Invite
panel member, token, sent, opened, reminders
Token is the expert's only credential
Response
panel member, mode, content, attestation, submitted at
Form answers, document text or call transcript
ScreenResult
response, result, flags, redactions, reviewer
Accepted, redacted, held, rejected
Payment
case, type (hold, capture, release), amount
Customer side
Payout
response, amount, status
Expert side; created only after acceptance
SynthesisVersion
case, version, content, confidence by sub-question
One per accepted response
AuditEvent
case, actor, event type, detail, previous hash
Append-only
A global SuppressionEntry (expert identifier, date) backs the do-not-contact rule.
Pages and screens
The site has 8 customer pages, 8 expert pages and 3 admin pages. Experts never log in: every expert page hangs off the invite token.
Page
Who
What it does
Login and signup
Customer
Work email, terms
Workspace settings
Customer admin
Restricted list, cooling-off, freshness, blackout, budget, approvers
Ask
Customer
Question, target company, panel size, budget, deadline
Plan review
Customer
Sub-questions, target roles, coverage target, approve and authorise hold
Live case
Customer
Candidate pool, badges, panel status, coverage meter, response cards, live synthesis
Memo
Customer
Verdict, confidence, per sub-question view, citations, export
Audit trail
Customer admin
Full log, filters, export
Case list
Customer
Past and active cases, spend
Invite landing
Expert
Topic, payout, ground rules, attestations, accept or decline
Mode choice
Expert
Form, doc or AI call
Form
Expert
Generated questions, autosave, I-can't-answer option
Doc upload
Expert
Own-words document or template
AI call
Expert
Compliance script, interview, live transcript
Review and submit
Expert
Anonymised preview, redact, re-attest
Done
Expert
Screen result, payout status, optional profile
Preferences
Expert
Topics, rates, recontact, do-not-contact, delete my data
Review queue
Reviewer
Held responses and flagged experts
Cases and spend
Reviewer
All cases, refunds, disputes
Suppression and settings
Reviewer
Do-not-contact list, default rules
Hackathon scope
Build the whole flow for real inside the 7-hour window, but never contact real people: emails go only to teammates through an approval queue, and payments are a labelled simulation.
Treatment
What
Build for real
Ask and plan, question screen, Crustdata sourcing, people screen, ranking, approval queue, expert page with form, response screen, live case page, synthesis and memo, audit trail and cost log
Build if time allows
Browser voice interview with the leak-refusal behaviour (typed chat is its fallback), Crustdata company-data check
Simulate and label
Payments and payouts: a ledger of holds, captures and payouts released by an approve click, marked "simulated" in the UI and README
Restrict
Email goes only to a hard-coded list of teammate addresses, enforced in code and shown refusing a non-teammate address
Do not build
Customer signup (one pre-made account), doc upload, reviewer queue, invite delivery tracking, expert profiles and preferences, follow-up questions, multiple organisations, refund logic beyond the ledger, privacy and legal review
Build order
1.  0:00 to 0:45: repo skeleton and the Crustdata coverage test.
2.  0:45 to 2:30: ask, plan, sourcing, people screen, ranking and the panel view.
3.  2:30 to 4:00: expert page and form, approval queue, response storage.
4.  4:00 to 5:15: response screen, synthesis, memo and live case page. One full case must run by 5:15.
5.  5:15 to 6:15: browser voice interview with leak refusal, audit trail and cost log.
6.  6:15 to 7:00: README, architecture diagram, demo video, final commit.
Demo setup. At the finals, run an unseen question live with caching off. Teammates play the experts on their own devices: one answers by form and one by voice. Only registered team members may operate the service, so judges and real people are not used as experts. The memo and confidence update as each answer lands. Say plainly which part is simulated (the payment ledger).
Open questions and edge cases
Five facts must be checked in the first hour on the day, and the edge-case rules below should be settled before they come up in a demo.
To verify
[ ] Does Crustdata's Person search filter on past employer, and does it return exit dates?
[ ] Does it return usable emails, or only profiles? Outreach goes only to teammates either way, so this only affects what the sourcing screen can show.
[ ] Does company enrich return function-level headcount, or only total headcount?
[ ] What does each search and enrich call cost in credits?
[ ] What are Crustdata's terms on storing and using people data?
Ask the help desk at kickoff
[ ] Is a teammate typing a persona's answer on the expert page acceptable (rule 3.3 versus rule 5.5)?
[ ] Are web search and fetch permitted APIs, or only Crustdata and the model?
[ ] Is a dev-time cache of real API responses allowed, if it is switched off for the finals run?
Decisions still open
[ ] Price per answered sub-question and expert payout.
[ ] Single-source sub-questions: charge at a reduced rate, or deliver free.
[ ] Payout rails, tax handling and identity checks for experts in India and abroad.
[ ] Legal review of outreach and storage under India's DPDP Act and the GDPR.
Edge cases
Situation
Rule
Expert submits twice
Latest submitted response replaces the earlier one; earlier is kept in the audit trail
Expert wants to retract
Allowed until the case closes; withdrawn response leaves the synthesis and a new version is issued
Expert turns out to be a current employee
Response rejected, not paid, expert added to suppression for that company, logged
Everyone rejected or no reply
Case closes with nothing charged and a note on what to change (wider window, other roles)
One expert invited by two cases
Allowed only if the topics differ; otherwise the second invite waits 14 days
Customer's restricted list includes the target
Case blocked at the ask step
Customer asks for a prohibited question
Rejected with reason and suggested rewrite
Responses contradict the company data
Shown as a disagreement, confidence capped at Low
Expert is a referral (names someone else)
Referral goes to the screen as a new candidate; never contacted before screening
Time zones
Deadlines in the customer's zone, reminders in the expert's