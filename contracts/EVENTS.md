# Events

Written 2026-11-22 by Dev. Append-only: a change needs a message to the other person first.

Every event is a row in the hash-chained `events` table and is sent live on `GET /cases/{id}/events` (server-sent events). Each message has `id:` (the event id, usable as `Last-Event-ID` or `?after=`), `event:` (the type) and `data:` (JSON). The JSON always has `id`, `type`, `at` (UTC time) and the fields below.

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `case.created` | `question` | A case was created. |
| `case.state` | `state` (see ENUMS.md), `reason` on `REFUSED` | The case changed state. |
| `stage.started` | `stage` | A stage began. |
| `stage.done` | `stage`, `result` | A stage finished. `result` is the stage result (see API.md). |
| `stage.failed` | `stage`, `error` | A stage raised an error. A `case.state` of `FAILED` follows. |
| `crustdata.call` | `call_id`, `endpoint`, `purpose`, `status`, `credits`, `cache_hit` | One Crustdata call and its cost in credits. `call_id` is what memo claims cite. |
| `llm.call` | `call_id`, `purpose`, `model`, `attempt`, `tokens_in`, `tokens_out`, `cost_usd`, `valid` | One model call and its cost. |
| `job.paused` | `reason` | The job reached the end of what is built. The stream closes after this event. |

The stream also closes after a `case.state` of `REFUSED` or `FAILED`. Events carry no secrets. `stage.done` results include candidate details, which are real people's profile data: show them in the app, never put them in the README or a screenshot in the repo.
