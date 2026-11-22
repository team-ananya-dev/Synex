-- Ananya-owned tables (expert side and synthesis). Loaded automatically by app.core.db.
-- Append-only like the core tables: triggers block UPDATE and DELETE.

-- One row per answer to one sub-question. Nobody edits an answer after it is submitted.
CREATE TABLE IF NOT EXISTS responses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id       TEXT NOT NULL UNIQUE,   -- cited by memo claims, for example "R3fa91c20"
    case_id           TEXT NOT NULL,
    outreach_id       INTEGER NOT NULL,
    person_id         INTEGER NOT NULL,       -- the candidate whose persona this answer is for
    subquestion_index INTEGER NOT NULL,
    mode              TEXT NOT NULL,          -- form | voice | text
    kind              TEXT NOT NULL,          -- answer | dont_know | confidential
    text              TEXT NOT NULL,          -- empty unless kind = answer
    confidence        TEXT,                   -- low | medium | high (self-rated), null unless kind = answer
    attestations      TEXT NOT NULL,          -- JSON: the four ticks on the expert page
    created_at        TEXT NOT NULL,
    UNIQUE (outreach_id, subquestion_index)
);

CREATE TRIGGER IF NOT EXISTS responses_no_update BEFORE UPDATE ON responses
BEGIN SELECT RAISE(ABORT, 'responses is append-only'); END;
CREATE TRIGGER IF NOT EXISTS responses_no_delete BEFORE DELETE ON responses
BEGIN SELECT RAISE(ABORT, 'responses is append-only'); END;

-- Stage 7: one row per screening decision. The first row comes from the screen; a held response gets a
-- second row when a team member accepts or rejects it. Readers take the latest row per response_id.
CREATE TABLE IF NOT EXISTS response_screens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     TEXT NOT NULL,
    verdict         TEXT NOT NULL,          -- accepted | redacted | held | rejected
    reason          TEXT NOT NULL,
    redacted_text   TEXT,                   -- the answer with flagged spans removed, only for redacted
    flagged_spans   TEXT NOT NULL,          -- JSON list of exact quotes the screen flagged (verified in code)
    code_flags      TEXT NOT NULL,          -- JSON list of risk phrases found by the code rule
    llm_call_id     TEXT,                   -- the model call behind this verdict, null for code-only or human rows
    decided_by      TEXT NOT NULL,          -- "screen", or the team member who reviewed a held response
    created_at      TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS response_screens_no_update BEFORE UPDATE ON response_screens
BEGIN SELECT RAISE(ABORT, 'response_screens is append-only'); END;
CREATE TRIGGER IF NOT EXISTS response_screens_no_delete BEFORE DELETE ON response_screens
BEGIN SELECT RAISE(ABORT, 'response_screens is append-only'); END;
