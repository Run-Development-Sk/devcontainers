---
description: >-
  Entry point to the run-save-response skill – save the last prompt and response
  outside any save interaction verbatim to a .md file.
---

# /run.save-response – Save last prompt and response to .md

Follow the procedure according to the **`run-save-response`** skill (`.agents/skills/run-save-response/SKILL.md`). The command and the skill have the same output; this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not support slash commands – use the `run-save-response` skill directly there.)

In short (details in the skill):

1. Determine the agent's suffix (`auggie` / `claude` / `agy` / `codex`).
2. Determine which pair to save – the most recent prompt and response that are not part of a save interaction (`/run.save-response`, `/run.save-chat`, their skills, or a free-text save request, together with the turns answering it).
3. Determine the target path:
   - without an argument -> ask the user whether to auto-generate the name (slug from the topic of the saved response, folder `tmp/`) or if they want to enter it,
   - name without a folder -> folder `tmp/`,
   - name with a folder -> stays in that folder,
   - missing extension -> append `.md`.
4. Add the suffix `-<agent>` before `.md` (e.g., `my-tax-analyze-auggie.md`).
5. Write the **literal** (verbatim) selected prompt and response, delimited by `PROMPT` / `RESPONSE` separator lines (exact file format in the skill) – and announce the resulting path.

Hard rules: the prompt and response are verbatim – a command/skill invocation in a prompt stays an invocation and is never expanded into its content; save interactions are never saved; the agent suffix is always added; no secrets in the file (`.agents/rules/run.secret-safety.md`).

If the user provided an argument (name, potentially with a folder), narrow the procedure accordingly.
