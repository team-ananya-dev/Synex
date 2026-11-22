# From Ananya: README and architecture diagram drafted, please check the claims about your half

`README.md` (root) and `docs/ARCHITECTURE.md` are on main. The team README says each of us writes one section, but I drafted the whole thing from your progress log, the contracts and the code so we do not start from a blank page at the end. Please read it and correct anything about your modules. Rule 7: every claim must match what the code does.

I checked each claim in the code, and found two things the README now says plainly:

- Every model call uses the small model (`claude-haiku-4-5-20251001`). `LARGE_MODEL` is defined in `server/app/core/llm.py` but no stage uses it. If you plan to use it, say so; otherwise the old "large model only for the memo" line must not appear anywhere.
- The restricted list exists in `s4_people_screen.py` but is empty. The README says so.

Please check in particular:
1. The people screen section (defaults, each rule, the competitor behaviour, what is not built: closed period and do-not-contact).
2. "Approvals": one customer click approves the batch, each email still has its own `approval.approved` event, flagged invitations start unselected. This matches your decision record. The help desk question is listed as open.
3. "Audit trail and cost log": the $25 model budget and the per-case Crustdata credit cap are in code.
4. The Run section (commands and flags) and the Credits section. Your progress log lists FastAPI, Uvicorn, httpx, pydantic, pytest, the Anthropic SDK, uv and Mailpit v1.34.0, which I copied. Add anything you installed that is missing.
5. The `Open questions for the organisers` list: tell me which of them you have actually asked, and I will move those out.

Not in the README yet: the demo video link. It needs a real recording.
