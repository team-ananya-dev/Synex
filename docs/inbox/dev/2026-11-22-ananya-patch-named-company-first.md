# From Ananya: ready patch for the named-company issue

Follows `2026-11-22-ananya-named-company-marked-inferred.md`. Your files, so I did not commit to them; this is a patch you can apply as is or rewrite.

What it does: after the decomposer reply, the basis of each target company is set in code (`named` exactly when the name is in the question) and named companies are sorted first, so the per-sub-question company limit never drops the company the customer asked about. Adds one test. With it, 72 tests pass (your 71 plus the new one).

Apply from the repo root:

```
sed -n '/^```diff$/,/^```$/p' docs/inbox/dev/2026-11-22-ananya-patch-named-company-first.md | sed '1d;$d' | git apply
cd server && .venv/bin/python -m pytest -q
```

```diff
diff --git a/server/app/stages/s2_decomposer.py b/server/app/stages/s2_decomposer.py
index 6905d94..b59dcf7 100644
--- a/server/app/stages/s2_decomposer.py
+++ b/server/app/stages/s2_decomposer.py
@@ -74,6 +74,14 @@ def decompose(conn, question: str, case_id: str | None) -> tuple[list[dict], str
             "text": s["text"].strip(),
             "expertise": s["expertise"].strip(),
             "title_keywords": [k.strip() for k in s["title_keywords"] if k.strip()],
-            "target_companies": s["target_companies"],
+            "target_companies": _order_companies(question, s["target_companies"]),
         })
     return subs, call_id
+
+
+def _order_companies(question: str, companies: list[dict]) -> list[dict]:
+    """Basis is decided in code: a company is "named" exactly when its name is in the question.
+    Named companies come first, so the per-sub-question company limit never drops one."""
+    q = question.lower()
+    out = [{"name": c["name"], "basis": "named" if c["name"].lower() in q else "inferred"} for c in companies]
+    return sorted(out, key=lambda c: c["basis"] != "named")
diff --git a/server/tests/test_decomposer.py b/server/tests/test_decomposer.py
index d2aeb75..7bea58a 100644
--- a/server/tests/test_decomposer.py
+++ b/server/tests/test_decomposer.py
@@ -34,3 +34,10 @@ def test_named_company_must_appear_in_question():
     with pytest.raises(ValueError, match="not in the question"):
         validate("What does a rival do?", reply())
     validate("What does a rival do?", reply(target_companies=[{"name": "Acme", "basis": "inferred"}]))
+
+
+def test_company_in_question_is_named_and_first():
+    from app.stages.s2_decomposer import _order_companies
+    q = "How is the delivery business doing at Acme Foods?"
+    got = _order_companies(q, [{"name": "Rival Co", "basis": "inferred"}, {"name": "Acme Foods", "basis": "inferred"}])
+    assert got == [{"name": "Acme Foods", "basis": "named"}, {"name": "Rival Co", "basis": "inferred"}]
```
