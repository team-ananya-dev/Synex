# 2026-11-22 (Dev, results session): after an expert submits

Append-only. Written by Dev's second session (branch `dev/results`) at about 15:25 IST. For Ananya's web screens.

## Ownership note (please read, Ananya)
`OWNERS.md` lists stage 8 as yours. Dev has taken the **result computation** (`server/app/stages/s8_result.py`, `server/app/routes/result.py`) so that you can stay on the web screens. Please do not start a second s8. If you already have, message Dev and we pick one. Stage 7 stays yours as pushed; nothing in it changes.

## 1. Stage 7 event (already on main, restated)
`response.screened`: `{"response_id", "subquestion_index", "verdict": "accepted" | "redacted" | "held" | "rejected", "by": "screen" | <team member>}`. No text, no reason. Same payload on the operator and customer streams. A held answer gets a second `response.screened` when a team member decides. **New:** after every `response.screened`, read `GET /customer/cases/{id}/result` again; the result is computed fresh on each read.

## 2. Answers grouped by sub-question (already on main)
Use `GET /customer/cases/{id}/responses` (Ananya's, see API.md "stage 7"). It already returns anonymised cards and per-sub-question coverage counts. No new answers route.

## 3. `GET /customer/cases/{id}/result` (customer-safe, new)
Computed in code from the latest screen row of every response. Only `accepted` and `redacted` answers count (redacted ones with the spans removed). No names, links, emails, cities or person ids.
```
{
  "case_id", "question", "state",
  "computed_at",
  "subquestions": [{
    "index", "text",
    "status": "answered" | "no accepted answer",
    "coverage": {"received", "pending", "accepted", "redacted", "held", "rejected"},
    "answers": [{"ref", "response_id", "role", "company", "verdict": "accepted" | "redacted", "text", "confidence", "mode"}],
    "independent_sources": int,             // 0 when no accepted answer
    "groups": [{"refs": [str], "evidence": str}],   // one group = one independent source
    "independence_unchecked": [{"ref", "missing": [str]}],  // work-history fields missing; counted as separate
    "label": "single source" | "consensus" | "split" | "multiple sources, agreement not assessed" | null,
    "label_basis": "code" | "model",
    "confidence": "High" | "Medium" | "Low" | null,   // High >= 3 independent sources, Medium 2, Low 1, null at 0
    "summary": null | {"sentences": [{"text", "cites": [ref]}], "dropped_uncited": int, "llm_call_id"}
  }],
  "summary_status": "not written" | "written" | "stale"   // stale: answers changed since the summary was written
}
```
Rules, all in code:
- **Independent sources.** Two answers to one sub-question are one source when both experts worked at the same company, in the same function, list the same city on their profile, and their roles there overlapped by at least 3 months (Crustdata work history from stage 3). `evidence` says which of these matched and the overlap in months, with no city named. If a field is missing for an expert, they count as a separate source and appear in `independence_unchecked`.
- **Label.** 1 source: `single source`. 2 or more: `consensus` or `split` only after the summary is written (the model judges agreement and `label_basis` is `model`); before that, `multiple sources, agreement not assessed`. `null` with no accepted answer.
- `404` unknown case.

## 4. `POST /customer/cases/{id}/result/summary` (new, optional step)
Writes 1 to 3 sentences per answered sub-question with the small model (one call per case, logged in `llm_calls`). Each sentence must cite at least one `[ref]` of an answer to that sub-question. A checker in code drops any sentence without a valid citation and counts it in `dropped_uncited`. Stored append-only in `stage_results` (stage `s8_summary`), keyed on the set of answers used: a second click with the same answers returns the stored summary and makes no model call. Returns the same body as `GET .../result`. `404` unknown case, `409` no accepted answer yet, `503` model failed or budget reached (the structured result is still valid; show it without prose).
Event: `result.summary_written` `{"llm_call_id", "subquestions": [index], "dropped_uncited": int}`.
