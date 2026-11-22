"""The one place that calls the model.

Every call is logged to llm_calls (prompt, response, tokens, dollars) and the
audit chain. Replies are structured: the model must answer through a single
tool whose input schema is the expected JSON. A reply that fails validation is
retried once with the error shown to the model.
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Callable

import anthropic

from . import config
from .events import append_event

SMALL_MODEL = os.environ.get("SYNEX_SMALL_MODEL", "claude-haiku-4-5-20251001")
LARGE_MODEL = os.environ.get("SYNEX_LARGE_MODEL", "claude-sonnet-5-5")

# Dollars per million tokens (input, output). Confirm against the Anthropic
# console before the demo; override with SYNEX_PRICE_<MODEL> if they differ.
PRICES = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}
BUDGET_USD = float(os.environ.get("SYNEX_LLM_BUDGET_USD", "25"))


class BudgetExceeded(RuntimeError):
    pass


class InvalidModelReply(RuntimeError):
    pass


def _price(model: str) -> tuple[float, float]:
    if model not in PRICES:
        raise RuntimeError(f"no price known for {model}; add it to PRICES from the console")
    return PRICES[model]


def spent_usd(conn: sqlite3.Connection) -> float:
    return float(conn.execute("SELECT COALESCE(SUM(cost_usd),0) c FROM llm_calls").fetchone()["c"])


def call_json(
    conn: sqlite3.Connection,
    *,
    purpose: str,
    system: str,
    user: str,
    schema: dict,
    validate: Callable[[dict], None] | None = None,
    model: str = SMALL_MODEL,
    case_id: str | None = None,
    max_tokens: int = 1500,
    client: anthropic.Anthropic | None = None,
) -> tuple[dict, str]:
    """Return (validated reply, call_id of the accepted attempt)."""
    if client is None:
        key = os.environ.get("SYNEX_ANTHROPIC_KEY")
        if not key:
            raise RuntimeError("SYNEX_ANTHROPIC_KEY is not set in .env")
        client = anthropic.Anthropic(api_key=key)

    in_price, out_price = _price(model)
    tool = {"name": "respond", "description": "Return the answer as JSON.", "input_schema": schema}
    messages = [{"role": "user", "content": user}]
    error = None

    for attempt in (1, 2):
        if spent_usd(conn) >= BUDGET_USD:
            raise BudgetExceeded(f"model spend {spent_usd(conn):.2f} USD reached the {BUDGET_USD} USD budget")
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages,
            tools=[tool], tool_choice={"type": "tool", "name": "respond"},
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        reply = block.input if block else None
        error = None
        if reply is None:
            error = "no structured reply"
        elif validate:
            try:
                validate(reply)
            except (ValueError, KeyError, TypeError) as e:
                error = str(e)

        call_id = uuid.uuid4().hex
        cost = (resp.usage.input_tokens * in_price + resp.usage.output_tokens * out_price) / 1_000_000
        conn.execute(
            "INSERT INTO llm_calls (call_id, case_id, purpose, model, prompt, response, input_tokens,"
            " output_tokens, cost_usd, attempt, valid, error, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (call_id, case_id, purpose, model, json.dumps({"system": system, "messages": messages}),
             json.dumps(reply), resp.usage.input_tokens, resp.usage.output_tokens, cost, attempt,
             int(error is None), error, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        append_event(conn, case_id, "llm.call", {
            "call_id": call_id, "purpose": purpose, "model": model, "attempt": attempt,
            "tokens_in": resp.usage.input_tokens, "tokens_out": resp.usage.output_tokens,
            "cost_usd": round(cost, 6), "valid": error is None,
        })
        if error is None:
            return reply, call_id
        if block:
            messages = messages + [
                {"role": "assistant", "content": [{"type": "tool_use", "id": block.id, "name": "respond", "input": reply}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id,
                                              "content": f"Invalid: {error}. Answer again.", "is_error": True}]},
            ]
        else:
            messages = messages + [{"role": "user", "content": f"Invalid: {error}. Answer again through the tool."}]
    raise InvalidModelReply(f"{purpose}: {error}")
