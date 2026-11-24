"""API keys supplied by the person using the site (bring your own key).

The browser sends its keys with every request, in the X-Anthropic-Key and X-Crustdata-Key headers. The server keeps
them in memory only, per case, so the background jobs of that case can use them. They are never written to the
database, the audit trail, the cost log or any response. A key missing from the case falls back to the server's
.env (SYNEX_ANTHROPIC_KEY, CRUSTDATA_API_KEY): that is how a local clone runs. A hosted site with no .env keys
makes every visitor use their own.
"""
import os
import re
import threading

ANTHROPIC_HEADER = "x-anthropic-key"
CRUSTDATA_HEADER = "x-crustdata-key"
_CASE_PATH = re.compile(r"^/(?:customer/)?cases/([^/]+)")
_MAX_CASES = 500   # oldest entries drop first, so memory stays bounded

_lock = threading.Lock()
_by_case: dict[str, dict[str, str]] = {}


class MissingKey(RuntimeError):
    pass


def _clean(value: str | None) -> str:
    return (value or "").strip()   # a pasted key can carry a newline, which breaks the header


def from_headers(headers) -> dict[str, str]:
    out = {}
    for name, header in (("anthropic", ANTHROPIC_HEADER), ("crustdata", CRUSTDATA_HEADER)):
        v = _clean(headers.get(header))
        if v:
            out[name] = v
    return out


def case_id_from_path(path: str) -> str | None:
    m = _CASE_PATH.match(path)
    return m.group(1) if m and m.group(1) != "" else None


def remember(case_id: str, given: dict[str, str]) -> None:
    if not given:
        return
    with _lock:
        _by_case.pop(case_id, None)
        _by_case[case_id] = {**_by_case.get(case_id, {}), **given}
        while len(_by_case) > _MAX_CASES:
            _by_case.pop(next(iter(_by_case)))


def _find(name: str, case_id: str | None) -> tuple[str, bool]:
    """(key, supplied_by_user). Empty key when none is available."""
    if case_id:
        with _lock:
            k = _by_case.get(case_id, {}).get(name)
        if k:
            return k, True
    env = "SYNEX_ANTHROPIC_KEY" if name == "anthropic" else "CRUSTDATA_API_KEY"
    return _clean(os.environ.get(env)), False


def anthropic(case_id: str | None = None) -> tuple[str, bool]:
    key, mine = _find("anthropic", case_id)
    if not key:
        raise MissingKey("No Anthropic API key. Add yours on the Ask page (or set SYNEX_ANTHROPIC_KEY in .env when running locally).")
    return key, mine


def crustdata(case_id: str | None = None) -> str:
    key, _ = _find("crustdata", case_id)
    if not key:
        raise MissingKey("No Crustdata API key. Add yours on the Ask page (or set CRUSTDATA_API_KEY in .env when running locally).")
    return key


def require(case_id: str | None, given: dict[str, str], *names: str) -> None:
    """Refuse a request up front when a key it needs is neither sent nor in .env."""
    for n in names:
        if n in given:
            continue
        if not _find(n, case_id)[0]:
            label = "Anthropic" if n == "anthropic" else "Crustdata"
            raise MissingKey(f"Add your {label} API key first.")


def scrub(text: str, case_id: str | None = None) -> str:
    """Remove any key from text before it is stored or shown."""
    with _lock:
        secrets = [v for d in ([_by_case.get(case_id, {})] if case_id else _by_case.values()) for v in d.values()]
    for s in secrets:
        text = text.replace(s, "[key]")
    return text
