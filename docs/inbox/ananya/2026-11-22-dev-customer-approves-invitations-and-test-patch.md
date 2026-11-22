# From Dev: invitations are now approved by the customer (two things for you)

Decision (Dev and the product owner, this afternoon): nobody approves emails one by one. The customer reads the anonymised invitations and approves them in one click; they are then sent. Details and the rulebook reasoning: `contracts/decisions/2026-11-22-dev-customer-approves-invitations.md`. Routes and shapes: `contracts/API.md`, the section "Changes 2026-11-22 (Dev): the customer approves the invitations".

I registered your expert router in `server/app/main.py` as you asked.

## 1. Your tests need a 3-line change (your file, so it is a patch)
`POST /approvals/{id}/approve` no longer exists, and your `sent` fixture in `server/tests/test_expert.py` used it. Without the patch three of your tests error. With it all four pass (I tried it on a copy).

Replace these two lines in the `sent` fixture:

```python
    assert client.post(f"/approvals/{item['id']}/approve", json={"approver": "ananya"}).json()["status"] == "SENT"
```
with:

```python
    refs = [i["ref"] for i in client.get(f"/customer/cases/{cid}").json()["invites"]]
    assert client.post(f"/customer/cases/{cid}/approve-outreach", json={"refs": refs}).json()["sent"] == 1
```
Note: approving the invitations now sets the case to `COLLECTING` (I do it, in `routes.py`). Your `set_state(..., "COLLECTING")` on the first response is still fine, it is idempotent; if a test of yours asserts the state before the first response, expect `COLLECTING` instead of `AWAITING_APPROVAL`.

## 2. The web part (yours)
- `/operator/approvals` can no longer approve or reject. `GET /approvals` still works as a read-only list, so that page can stay as an operator "what was sent" log, or be dropped.
- The customer case page needs a new step when `state === "AWAITING_APPROVAL"`: "Review invitations". Use `data.invites` from `GET /customer/cases/{id}`: one row per expert (`ref`, `role`, `company`, `tenure_months`, `subject`, `preview`), a checkbox per row that starts ticked when `selected_by_default` is true, a warning with `flag_reasons` on flagged rows (unticked by default: the customer decides), then one button that posts the ticked `ref`s to `POST /customer/cases/{id}/approve-outreach {"refs": [...]}`. Show the result (`sent`, `dropped`) and let the existing live updates move the page to collecting.
- Never show a recipient address or link. The `preview` text has `[first name]` and `[private link]` placeholders on purpose: show it as is.
- In this competition every invitation goes to a teammate inbox through Mailpit. Do not claim on any screen that real experts were emailed.
