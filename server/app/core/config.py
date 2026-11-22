import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


def demo_mode() -> bool:
    return os.environ.get("SYNEX_DEMO") == "1"


def dev_cache_enabled() -> bool:
    return os.environ.get("SYNEX_DEV_CACHE") == "1" and not demo_mode()


def dev_limit() -> int | None:
    """Result cap per Crustdata search while developing. None in demo mode."""
    if demo_mode():
        return None
    return int(os.environ.get("SYNEX_DEV_LIMIT", "5"))


def db_path() -> Path:
    return Path(os.environ.get("SYNEX_DB", ROOT / "data" / "synex.db"))


def crustdata_key() -> str:
    key = os.environ.get("CRUSTDATA_API_KEY", "")
    if not key:
        raise RuntimeError("CRUSTDATA_API_KEY is not set in .env")
    return key


def dev_max_subquestions() -> int | None:
    """Sub-questions sourced per case while developing. None in demo mode."""
    return None if demo_mode() else int(os.environ.get("SYNEX_DEV_SUBQUESTIONS", "2"))


def max_companies_per_subquestion() -> int:
    """Companies searched per sub-question. 3 in demo mode to bound credits, 1 while developing."""
    return 3 if demo_mode() else int(os.environ.get("SYNEX_DEV_COMPANIES", "1"))
