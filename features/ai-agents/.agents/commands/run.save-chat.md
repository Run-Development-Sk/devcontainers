---
description: >-
  Entry point to the run-save-chat skill – save the entire chat history except save
  interactions verbatim to a .md file.
---

# /run.save-chat – Save entire chat history to .md

Follow the procedure according to the **`run-save-chat`** skill (`.agents/skills/run-save-chat/SKILL.md`). The command and the skill have the same output; this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not support slash commands – use the `run-save-chat` skill directly there.)

In short (details in the skill):

1. Determine the agent's suffix (`auggie` / `claude` / `agy` / `codex`).
2. Determine which turns to skip – every save interaction (`/run.save-response`, `/run.save-chat`, their skills, or a free-text save request, together with the turns answering it).
3. Determine the target path:
   - without an argument -> ask the user whether to auto-generate the name (slug from the conversation topic, folder `tmp/`) or if they want to enter it,
   - name without a folder -> folder `tmp/`,
   - name with a folder -> stays in that folder,
   - missing extension -> append `.md`.
4. Add the suffix `-<agent>` before `.md` (e.g., `my-chat-auggie.md`).
5. Write the **literal** (verbatim) content of the entire conversation – **all** saved prompts and responses in chronological order, delimited by `PROMPT` / `RESPONSE` separator lines (exact file format in the skill) – and announce the resulting path.

Hard rules: prompts and responses are verbatim – a command/skill invocation in a prompt stays an invocation and is never expanded into its content; the entire chat history is saved (not just the last turn) except the skipped save interactions; the agent suffix is always added; no secrets in the file (`.agents/rules/run.secret-safety.md`).

If the user provided an argument (name, potentially with a folder), narrow the procedure accordingly.
