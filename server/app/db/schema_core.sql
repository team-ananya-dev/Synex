-- Dev-owned tables. Append-only tables block UPDATE and DELETE with triggers.

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT,
    type        TEXT NOT NULL,
    payload     TEXT NOT NULL,           -- JSON
    created_at  TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crustdata_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id     TEXT NOT NULL UNIQUE,    -- cited by memo claims
    case_id     TEXT,
    purpose     TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    request     TEXT NOT NULL,           -- JSON, as sent (after any dev limit)
    status      INTEGER,
    credits     REAL NOT NULL DEFAULT 0, -- from the X-Credits-Used header
    latency_ms  INTEGER,
    cache_hit   INTEGER NOT NULL DEFAULT 0,
    response    TEXT,                    -- JSON, full body
    error       TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id       TEXT NOT NULL UNIQUE,
    case_id       TEXT,
    purpose       TEXT NOT NULL,
    model         TEXT NOT NULL,
    prompt        TEXT NOT NULL,
    response      TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    cost_usd      REAL,
    attempt       INTEGER NOT NULL DEFAULT 1,
    valid         INTEGER,
    error         TEXT,
    created_at    TEXT NOT NULL
);

-- Development only. Never read or written when SYNEX_DEMO=1.
CREATE TABLE IF NOT EXISTS dev_cache (
    key         TEXT PRIMARY KEY,
    endpoint    TEXT NOT NULL,
    response    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;

CREATE TRIGGER IF NOT EXISTS crustdata_calls_no_update BEFORE UPDATE ON crustdata_calls
BEGIN SELECT RAISE(ABORT, 'crustdata_calls is append-only'); END;
CREATE TRIGGER IF NOT EXISTS crustdata_calls_no_delete BEFORE DELETE ON crustdata_calls
BEGIN SELECT RAISE(ABORT, 'crustdata_calls is append-only'); END;

CREATE TRIGGER IF NOT EXISTS llm_calls_no_update BEFORE UPDATE ON llm_calls
BEGIN SELECT RAISE(ABORT, 'llm_calls is append-only'); END;
CREATE TRIGGER IF NOT EXISTS llm_calls_no_delete BEFORE DELETE ON llm_calls
BEGIN SELECT RAISE(ABORT, 'llm_calls is append-only'); END;

-- Case job runner. cases is the only mutable table here; every state change is also an audit event.
CREATE TABLE IF NOT EXISTS cases (
    id             TEXT PRIMARY KEY,
    question       TEXT NOT NULL,
    state          TEXT NOT NULL,
    refusal_reason TEXT,
    params         TEXT NOT NULL,        -- JSON: min_left, max_left, min_years
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

-- One row per finished stage. A rerun adds a row; readers take the latest per stage.
CREATE TABLE IF NOT EXISTS stage_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT NOT NULL,
    stage       TEXT NOT NULL,
    result      TEXT NOT NULL,           -- JSON
    created_at  TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS stage_results_no_update BEFORE UPDATE ON stage_results
BEGIN SELECT RAISE(ABORT, 'stage_results is append-only'); END;
CREATE TRIGGER IF NOT EXISTS stage_results_no_delete BEFORE DELETE ON stage_results
BEGIN SELECT RAISE(ABORT, 'stage_results is append-only'); END;

-- Outreach drafts and their approval. status: DRAFTED, SENT, REJECTED, BLOCKED (not on the allowlist), FAILED (mail error).
-- Every status change is also an audit event. to_address is always a teammate: no expert address is ever stored.
CREATE TABLE IF NOT EXISTS outreach (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id            TEXT NOT NULL,
    person_id          INTEGER NOT NULL,
    name               TEXT,                 -- operator view only
    persona_title      TEXT,
    persona_company    TEXT,
    tenure_months      INTEGER,
    subquestion_indices TEXT NOT NULL,       -- JSON list
    flags              TEXT NOT NULL,        -- JSON: screen reasons the approver must see
    token              TEXT NOT NULL UNIQUE, -- private link to the expert page
    to_address         TEXT NOT NULL,
    subject            TEXT NOT NULL,
    body               TEXT NOT NULL,
    status             TEXT NOT NULL,
    decided_by         TEXT,
    decided_at         TEXT,
    sent_at            TEXT,
    block_reason       TEXT,
    llm_call_id        TEXT,
    created_at         TEXT NOT NULL,
    UNIQUE (case_id, person_id)
);

-- Simulated ledger. Every amount is labelled simulated; no real payment exists anywhere in this system.
-- kind: HOLD (plan approved), CAPTURE (a sub-question answered by enough independent experts), RELEASE (unused hold returned).
CREATE TABLE IF NOT EXISTS ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    amount      REAL NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'USD (simulated)',
    ref         TEXT,
    note        TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
