---
description: Catch up on the other person's work and my inbox before starting or pushing
---
My name is the output of `git config user.name`, in lowercase. The other person is the other name in docs/TEAM_README.md section 3.

1. Run `git fetch origin`.
2. Show `git log origin/main --oneline -20` and `git diff --stat HEAD...origin/main`.
3. Read the other person's progress log in docs/progress/, from its newest entry back to the entry before it. Do not read my own.
4. List files that are new or changed since my last pull in `contracts/`, `docs/inbox/<my name>/` and `docs/inbox/`: `git diff --name-status HEAD...origin/main -- contracts docs/inbox`.
5. Summarise in at most 10 lines: what changed in areas I depend on, anything addressed to me, any contract or decision change, and anything that may conflict with my current branch.

Do not edit any file. Do not merge or rebase. End by asking me whether to pull.
