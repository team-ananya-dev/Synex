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
