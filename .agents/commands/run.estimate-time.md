---
description: >-
  Entry point to the run-estimate-time skill – read-only time estimate of a task, human-only
  and AI-assisted, with proposed overhead.
---

# /run.estimate-time – Time estimate of a task

Follow the procedure according to the **`run-estimate-time`** skill
(`.agents/skills/run-estimate-time/SKILL.md`). The command and the skill have the same output;
this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not
support slash commands – use the `run-estimate-time` skill directly there.)

In short (details in the skill):

1. Take the task from the argument (ask if missing); ask only about genuinely unclear points
   that neither the prompt nor the code answers (the testing scope only as part of such a
   question); the rest becomes explicit assumptions.
2. Inspect the source code read-only – the path from `docs/pm-project-info.md` >
   `**PM_PROJECT_PATH:**` if that file exists, otherwise the current project.
3. Break the task into sections and steps, each with `[<n>h]` (human) and `[ai:<n>h]`
   (AI-assisted), rounded up to 0.25 h, risky steps flagged; each section with an unbracketed
   subtotal (`6.5h ai:2.75h`).
4. Sum the steps and add the overhead by the skill's configuration tables.
5. Output assumptions, out of scope, implementation, overhead, total, and open questions.

Hard rule: this is **read-only** – the agent never edits, creates, or commits anything.

If the user provided an argument, use it as the task instead of asking again.
