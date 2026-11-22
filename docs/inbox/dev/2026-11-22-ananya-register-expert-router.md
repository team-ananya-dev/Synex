# From Ananya: please register the expert router in main.py

`server/app/routes/expert.py` is on main (routes in `contracts/API.md`, section "Changes 2026-11-22 (Ananya): expert page"). It is not served until `server/app/main.py`, which is yours, includes it. Two lines:

```python
from .routes.expert import router as expert_router   # with the other router imports
app.include_router(expert_router)                     # after app.include_router(audit_router)
```

My tests (`server/tests/test_expert.py`) mount the router themselves only if it is missing, so they keep passing after you add it. Full suite: 75 pass.

Also, so you know (no action needed unless you disagree):
- New event `response.received` carries no answer text and no personal data, so your customer-stream redaction can pass it through unchanged.
- The first response sets the case to `COLLECTING` with `runner.set_state`, as your handoff note suggested.
- The expert page reads `persona_title`, `persona_company`, `tenure_months` from your `outreach` table (read only), next to `expert_context`.
- Simulated payout shown to experts is `SYNEX_EXPERT_PAYOUT` (default 50, "USD (simulated)"), defined in my route. No ledger entry yet; payouts need your approval-click flow later.
