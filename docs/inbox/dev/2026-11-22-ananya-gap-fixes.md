# From Ananya: I changed some of your files (gap fixes from the full run)

Ananya asked me not to wait, so these went straight in. Please read before you touch these files, and pull first. All tests pass (111). Contract additions are in `contracts/API.md` ("Changes 2026-11-22 (Ananya): gaps found in the first full run") and `ENUMS.md`.

## Your files I edited
- `server/app/stages/s1_question_screen.py`: prompt says naming a company is not a reason to refuse or rewrite; the model lists `named_companies`; code keeps only names that appear in the question and, if a rewrite drops one, appends it to `effective_question`. New result fields `named_companies`, `restored_companies`. Checked live on the Blue Tokai question: the rewrite now keeps the company.
- `server/app/stages/s8_result.py`: (1) answers' `role` goes through the anonymity rule; (2) `status: "not sourced"` for sub-questions with no `s3_sourcer` entry; (3) summary prompt: `consensus`/`split` only for the same point, new agreement `different aspects` mapped to label `multiple sources, different aspects`.
- `server/tests/test_result.py`: one assertion now accepts `not sourced` and checks one exists in dev mode.

## New or mine
- `server/app/anonymity.py` (new): `coarse_role`, `anonymise_roles` (title kept only if 3 or more experts share it).
- `server/app/routes/responses.py`: coarse roles on the customer responses route; new `POST /customer/cases/{id}/close` (sets `DELIVERED` with `runner.set_state`).
- `server/app/routes/expert.py`: `screening` field for the expert after submitting; closed cases refuse new answers.
- `server/tests/test_gaps.py` (new, 8 tests).
- Web: Close case button and Delivered banner in the Result tab, `not sourced` shown honestly, expert outcome page.

## Not changed
Panel cards and invitations (`views.py`) still show exact titles before anyone answers. If you want the anonymity rule there too, `anonymise_roles` takes any list of dicts with `role` and `person_id`.

## Added later (demo-mode dry run)
- `server/app/stages/s6_outreach_writer.py`: `spread_by_company` picks the panel round-robin by company (each company's best first). Before, `panels[idx][:n]` could be all one company (Ananya's skincare case: every expert from the named brand).
- `server/app/crustdata/client.py`: I had also made 429 retry up to 6 times, but your rate-limit commit (e752f7c) landed at the same time and does the same with pacing. At the merge I kept **yours** and dropped mine (and my two tests). A demo-mode case had failed in stage 3 with `Rate limit exceeded for this endpoint` after about 14 calls in under a minute, before your fix.
- Tests: one more in `server/tests/test_gaps.py` (panel spread).
