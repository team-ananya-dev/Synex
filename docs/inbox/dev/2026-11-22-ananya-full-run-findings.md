# From Ananya: findings from a full run (case fef642d4ebc3, my local DB)

Everything from ask to cited summary worked: 9.5 Crustdata credits, $0.042 model spend, 0 invalid model calls, audit chain intact, no personal data on any customer route. Three things in your files:

## 1. The question screen drops a named company (most important)
Question: "How has customer demand for specialty coffee chains in India changed over the last two years, for example at Blue Tokai Coffee Roasters?"
Stage 1 verdict `rewrite`, reason: "mixes public market research ... with company-specific insights (Blue Tokai's performance) that may require confidential information". The rewrite was generic and did not contain the company, so the decomposer correctly marked every company `inferred` (Starbucks, Café Coffee Day first) and sourcing never searched Blue Tokai.
Asking what a named company's former staff saw first-hand is not a request for non-public data, and a judge's question will usually name a company. Suggest: tighten the stage 1 prompt so naming a company is not a reason to refuse or rewrite, and require any rewrite to keep every company name from the original question (checked in code: if a named company is missing from `rewritten_question`, reject the reply and retry once).

## 2. A "split" label on answers that do not contradict
Sub-question 2 had two answers: one about shifts to premium and cold drinks, one saying footfall held up (the rest was redacted). The summary step labelled it `split`, but the two sentences do not disagree. Suggest telling the model to answer `split` only when two answers make opposing claims about the same point, and `consensus` only when they support the same claim, and otherwise to say they address different aspects (which could stay "multiple sources, agreement not assessed").

## 3. Dev mode shows unsourced sub-questions as "no accepted answer"
With the dev limits only 2 of 5 sub-questions are sourced. The result lists all 5, and 3 to 5 say "no accepted answer". Harmless in demo mode. If easy, mark sub-questions that were never sourced (for example `status: "not sourced"`), so the page does not suggest experts failed to answer.

Small, from my side, fixed in `web/`: summary sentences already end with `[ref]` and also carry `cites`, so the page showed every citation twice; I now strip the trailing ref from the text for display. You may want the checker to store the clean sentence.
