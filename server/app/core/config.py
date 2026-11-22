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
    key = os.environ.get("CRUSTDATA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CRUSTDATA_API_KEY is not set in .env")
    return key


def dev_max_subquestions() -> int | None:
    """Sub-questions sourced per case while developing. None in demo mode."""
    return None if demo_mode() else int(os.environ.get("SYNEX_DEV_SUBQUESTIONS", "2"))


def max_companies_per_subquestion() -> int:
    """Companies searched per sub-question. 3 in demo mode to bound credits, 1 while developing."""
    return 3 if demo_mode() else int(os.environ.get("SYNEX_DEV_COMPANIES", "1"))


def enrich_top() -> int:
    """People per sub-question whose full profile is fetched (1 credit each). 5 in demo mode, 3 while developing."""
    return 5 if demo_mode() else int(os.environ.get("SYNEX_DEV_ENRICH", "3"))


def dev_drafts() -> int:
    """Outreach drafts per sub-question. 3 in demo mode, 2 while developing."""
    return 3 if demo_mode() else int(os.environ.get("SYNEX_DEV_DRAFTS", "2"))


def smtp_host() -> str:
    return os.environ.get("SYNEX_SMTP_HOST", "localhost")


def smtp_port() -> int:
    return int(os.environ.get("SYNEX_SMTP_PORT", "1025"))


def expert_base_url() -> str:
    return os.environ.get("SYNEX_EXPERT_BASE_URL", "http://localhost:3000").rstrip("/")


def price_per_subquestion_inr() -> float:
    """Quoted price per answered sub-question, in rupees. A display figure only: no payment is taken."""
    return float(os.environ.get("SYNEX_PRICE_PER_SUBQUESTION_INR", "8000"))


def case_credit_cap() -> float:
    """Crustdata credits one case may spend. 25 while developing (small limits), 250 in demo mode."""
    return float(os.environ.get("SYNEX_CASE_CREDIT_CAP", "250" if demo_mode() else "25"))


def web_origins() -> list[str]:
    """Browser origins allowed to call the API. The Next.js app is on port 3000; SYNEX_WEB_ORIGINS adds more (comma separated)."""
    extra = [o.strip() for o in os.environ.get("SYNEX_WEB_ORIGINS", "").split(",") if o.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000", *extra]


def operator_key() -> str:
    """When set (hosted deployments), operator routes need this key. Empty means open (local development)."""
    return os.environ.get("SYNEX_OPERATOR_KEY", "").strip()


def mailpit_api() -> str:
    return os.environ.get("SYNEX_MAILPIT_API", "http://localhost:8025").rstrip("/")


def send_delay_seconds() -> float:
    """Kill test only: a pause between invitation sends, so the process can be killed mid-batch. 0 normally."""
    return float(os.environ.get("SYNEX_SEND_DELAY_SECONDS", "0"))


def run_time_limit_seconds() -> float:
    """Wall-clock limit for one background phase of a case (planning, or sourcing to drafts)."""
    return float(os.environ.get("SYNEX_RUN_TIME_LIMIT_SECONDS", "900"))


def case_usd_cap() -> float:
    """Model spend one case may use, in dollars."""
    return float(os.environ.get("SYNEX_CASE_USD_CAP", "1.0"))


def usd_inr() -> float:
    """Rupees per dollar for the cost log. A configured rate, not a live quote."""
    return float(os.environ.get("SYNEX_USD_INR", "85"))


def inr_per_credit() -> float:
    """Rupees per Crustdata credit. 0 until the team sets the rate it pays; the credits are shown either way."""
    return float(os.environ.get("SYNEX_INR_PER_CREDIT", "0"))
