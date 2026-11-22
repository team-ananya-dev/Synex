# Request from Dev (results session): stage 7 idempotency and restart

Written 2026-11-22 about 15:25 IST. Your file, so this is a request, not an edit.

1. `s7_response_screen.screen_responses` writes a new `response_screens` row every time it runs. If it runs twice for one response, the answer is screened twice (two model calls, two events). Suggest: at the start of the loop, `if latest(conn, rid) is not None: continue`.
2. Screening runs as a FastAPI background task. If the server restarts between the submit and the screen, those responses stay `pending` forever. Suggest a startup sweep: every `responses` row with no `response_screens` row goes through `screen_responses` (safe once item 1 is in).

Stage 8 (`server/app/stages/s8_result.py`, Dev) reads only the latest screen row, so a double screen does not break the result, but it costs model spend and shows two events.
The result routes are in `contracts/2026-11-22-dev-results.md`. Read `GET /customer/cases/{id}/result` again after every `response.screened`.
