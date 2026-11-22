# From Ananya: a company named in the question was marked "inferred" and not searched

Found on a real dev run (case `cc1d86ae311f`, local DB), 2026-11-22.

Question: "How have customer acquisition costs and retention changed for electric scooter makers in India over the last two years, for example at Ather Energy?"

What happened: the decomposer listed `Hero MotoCorp, Bajaj Auto, TVS Motor, Ather Energy` for every sub-question, all marked `inferred`, with Ather Energy last. With the dev limit of 1 company per sub-question, only Hero MotoCorp was searched. The company the customer actually named was never sourced. In demo mode (3 companies) it would still be left out.

Why: `s2_decomposer.validate` only rejects `named` for a company that is *not* in the question. It does not catch the reverse (a company in the question marked `inferred`), and nothing puts named companies first.

Request (your files, `server/app/stages/s2_decomposer.py` or the runner):
1. After the reply, set `basis = "named"` in code for any company whose name appears in the question, instead of trusting the model's label.
2. Sort each sub-question's `target_companies` so `named` come first, before the per-sub-question company limit is applied.

Not urgent for my screens: the plan card already shows the basis per company. It matters for the demo, because a judge's question will usually name a company.
