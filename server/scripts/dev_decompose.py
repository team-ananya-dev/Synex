"""Development run of stage 2 on any question.

Usage: python scripts/dev_decompose.py "<question>"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import db, llm  # noqa: E402
from app.stages import s2_decomposer  # noqa: E402

question = sys.argv[1]
conn = db.connect()
subs, call_id = s2_decomposer.decompose(conn, question, "dev-decompose")
print(f"llm call {call_id}")
for s in subs:
    cos = ", ".join(f"{c['name']} ({c['basis']})" for c in s["target_companies"])
    print(f"\n{s['index']}. {s['text']}\n   expertise: {s['expertise']}\n   titles: {s['title_keywords']}\n   companies: {cos}")
print(f"\nmodel spend so far: ${llm.spent_usd(conn):.4f}")
