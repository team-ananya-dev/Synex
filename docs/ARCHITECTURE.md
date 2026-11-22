# Synex architecture

Diagrams are Mermaid, which GitHub renders in the browser. Everything shown here exists in the code.

## 1. System

One FastAPI process runs every stage, calls every outside service through a logging wrapper and writes everything to one SQLite file. The browser reads progress over one server-sent-events stream per case.

```mermaid
flowchart LR
  subgraph Browser["Browser (Next.js, port 3000)"]
    LP["Landing page"]
    CU["Customer: ask, plan, review invitations, live case, result"]
    OP["Operator: held answers, invitation log, audit trail, cost log"]
    EX["Expert page: private link, answer form"]
  end

  subgraph Server["FastAPI server (port 8000)"]
    CR["Customer routes<br/>/customer/..."]
    OR["Operator routes<br/>/cases /approvals /audit /operator"]
    ER["Expert routes<br/>/expert/{token}"]
    ST["Stages 1 to 8"]
    GATE["Mail gate<br/>teammate allowlist"]
    AUD["Audit chain<br/>hash-chained events"]
  end

  DB[("SQLite<br/>events, stage results, responses,<br/>crustdata_calls, llm_calls")]
  CD["Crustdata API<br/>people and company data"]
  AN["Anthropic API<br/>small model"]
  MP["Mailpit<br/>local inbox"]

  CU --> CR
  OP --> OR
  EX --> ER
  LP -. "starts a question" .-> CU
  CR --> ST
  ER --> ST
  ST -- "logged, credit-capped" --> CD
  ST -- "logged, budget-capped" --> AN
  ST --> GATE --> MP
  ST --> AUD --> DB
  CR -. "SSE stream" .-> CU
  OR -. "SSE stream" .-> OP
```

Customer routes never return a name, headline, profile link, city or email. Operator routes do, so they are separate and only the operator screens use them.

## 2. One case, start to finish

```mermaid
stateDiagram-v2
  [*] --> DRAFT: customer asks
  DRAFT --> REFUSED: stage 1 refuses
  DRAFT --> PLANNED: stages 1 and 2
  PLANNED --> SOURCING: customer approves the plan
  SOURCING --> AWAITING_APPROVAL: stages 3 to 6
  AWAITING_APPROVAL --> COLLECTING: customer approves the invitations
  COLLECTING --> COLLECTING: answers arrive, stage 7 screens each one
  DRAFT --> FAILED: a stage fails
  SOURCING --> FAILED: a stage fails
  REFUSED --> [*]
  FAILED --> [*]
```

Two human clicks gate the irreversible steps: the plan approval starts spending Crustdata credits, and the invitation approval is what lets email leave (to a teammate allowlist only). Every state change is an audit event.

## 3. The eight stages

```mermaid
flowchart TB
  S1["1 Question screen<br/>model: allow, rewrite or refuse"] --> S2["2 Plan<br/>model: 3 to 5 sub-questions<br/>code: marks companies named in the question"]
  S2 --> GA(["customer approves the plan"])
  GA --> S3["3 Sourcing<br/>Crustdata: company by id, then people search"]
  S3 --> S4["4 People screen<br/>rules in code, a reason for every result"]
  S4 --> S5["5 Ranking<br/>model scores, code checks every quoted evidence"]
  S5 --> S6["6 Invitations<br/>model drafts anonymised text"]
  S6 --> GB(["customer approves the invitations"])
  GB --> MAIL["Mail gate to teammate inbox"]
  MAIL --> EXP["Teammate answers as the persona on the expert page"]
  EXP --> S7["7 Response screen<br/>model proposes, code verifies, leak phrases held"]
  S7 --> S8["8 Result<br/>code: sources, label, confidence<br/>model: short cited summary"]
```

## 4. Where code decides and where the model decides

| Decision | Made by | Checked by |
| --- | --- | --- |
| Is the question allowed | small model | reason is shown; a refusal ends the case |
| Which companies were named in the question | code (whole-word match) | none needed |
| Which person fails the people screen | code, one function per rule | each result carries a reason |
| Which company record a name means | model chooses among ids Crustdata returned | code rejects an id that was not returned |
| How well a person fits | small model | code drops any quoted evidence that is not in the profile |
| Whether an answer is safe | small model proposes | code verifies quotes, holds on leak phrases, holds when the reply cannot be verified |
| How many independent sources | code, from work history | evidence is shown per group |
| Confidence | code (3 or more sources High, 2 Medium, 1 Low) | none needed |
| Agreement label and summary wording | small model | every sentence must cite an answer; code drops any that does not |

## 5. Data and the audit trail

- `events` is append-only and hash-chained: each row stores the previous row's hash and its own. `GET /audit/verify` recomputes the whole chain and names the first changed event.
- `crustdata_calls` and `llm_calls` are the cost log: every call, its purpose, its credits or tokens and its dollars. Prompts and responses are stored with each model call.
- `stage_results` and `responses` and `response_screens` are append-only too. A held answer is decided by adding a new row, never by editing text.
- SQLite triggers block UPDATE and DELETE on all of these tables.
