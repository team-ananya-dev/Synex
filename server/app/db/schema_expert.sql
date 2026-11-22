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
