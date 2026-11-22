---
description: Write my handoff entry, run the rule check, and prepare a commit
---
My name is the output of `git config user.name`, in lowercase.

1. Append an entry to docs/progress/<my name>.md using this template. Keep it short and factual.

```
## <date> <time> <my name> <session name>
Done: <what works now, with file paths>
In progress: <what is half done and where>
Next: <the next 1 to 3 tasks>
Decisions: <anything decided that others must know>
Blocked on: <person or file, with a deadline>
Contracts touched: <none, or which and the commit>
```

2. Run the rule-checker subagent on `git diff origin/main...HEAD` and report its findings.
3. Stage my changes and propose a commit message in the form `<area>: <what changed>`. The message must not contain any Claude, co-author or "generated with" line.
4. Do not push. Show me `git status`, `git log -3` and the diff stats, and wait.
