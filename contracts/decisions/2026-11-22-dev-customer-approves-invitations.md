# The customer approves the invitations, not the operator

Decided 2026-11-22 by Dev.

**What:** invitation emails are no longer approved one by one by a team member. The customer reviews the anonymised invitations and approves them with one click. Approved invitations are sent immediately, through the teammate-only allowlist gate. Invitations the customer leaves out are dropped. Experts with a review flag are not selected by default: the customer decides.

**Why:** the product promise is that experts are contacted for the customer once the customer agrees. An operator approving every email does not scale and does not match the site flow, where the customer approves the plan, the spend and the panel.

**Rulebook:** rule 4 says each irreversible action, such as an email or a payment, "waits for a person's approval". Each email still waits for a person's approval click; the person is the customer. One click can approve several emails, but each email gets its own `approval.approved` event with `by: "customer"` and its own `mail.sent`, `mail.blocked` or `mail.failed` event in the hash-chained audit trail. Nobody edits an email: the customer can only approve or drop. Payments stay simulated and labelled.

**To confirm with the help desk:** that one customer click on a batch of anonymised emails counts as "a person's approval" for each email. Until then the README must describe it exactly like this and claim no more.

**Not changed:** mail only goes to the teammate allowlist, enforced in code in `server/app/actions/mail.py`. The customer never sees a name, an address or the private link.
