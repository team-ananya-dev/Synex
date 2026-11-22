import sqlite3
from pathlib import Path

from . import config

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path) if path else config.db_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    for sql in sorted(SCHEMA_DIR.glob("schema_*.sql")):
        conn.executescript(sql.read_text())
    conn.commit()
