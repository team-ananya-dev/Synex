# docs/context

Files an agent reads for background. Some are in this pack; two you add by hand at kickoff.

In the pack:
- `00_PROJECT_CONTEXT.md`: everything decided in planning, self-contained.
- `01_RULEBOOK.pdf` and `01_RULEBOOK.txt`: the Participant Rulebook.
- `04_IDEA_BRIEF.pdf`: the brief, revised to match the rulebook.

Add at kickoff (Dev does this, a minute each):
- `02_SITE_FLOW.md`: open the document "Primary: Full Site Flow and Rules" in Claude, use its export menu, choose Markdown, and save it here under this name.
- `03_BUILD_GUIDE.md`: open "Primary: Developer Build Guide (7-hour)", export as Markdown, and save it here under this name.

If an export is missing, `00_PROJECT_CONTEXT.md` still carries the essentials, but the build guide has the architecture drawing's description, the data model, the stage table and the schedule, so add it.

The site flow describes the full product (accounts, pricing, refunds). The hackathon scope is smaller; where they differ, `00_PROJECT_CONTEXT.md` section 10 and the build guide win.


Naming note: "Primary" was the working name while these two documents were written. The project is now called Synex, so wherever those files say "Primary" (including env var `PRIMARY_ANTHROPIC_KEY`), read Synex and use `SYNEX_ANTHROPIC_KEY`.
