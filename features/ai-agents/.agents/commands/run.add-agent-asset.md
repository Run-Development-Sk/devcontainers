---
description: >-
  Entry point to the run-add-agent-asset skill – add a new agent artifact
  (skill, rule, slash command, or subagent) per docs/ai-agents.md.
---

# /run.add-agent-asset – Add agent artifact

Follow the procedure according to the **`run-add-agent-asset`** skill (`.agents/skills/run-add-agent-asset/SKILL.md`). The command and the skill have the same output; this command is the entry point for Claude Code, Auggie, and Antigravity. (Codex does not support slash commands – use the `run-add-agent-asset` skill directly there.)

Follow the `run-add-agent-asset` skill procedure:

1. Determine the artifact type (rule / skill / command / subagent).
2. Create file(s) in the correct location with mandatory frontmatter according to `docs/ai-agents.md` (source of truth); respect naming conventions and English language.
3. Sync documentation/registries according to the DoD checklist in the skill (always-apply and on-demand rules in `AGENTS.md`; new symlinks only for a new type of artifact).
4. Verify cross-tool discovery (Auggie / Claude / Antigravity / Codex).

If the user provided an argument (artifact type, name, purpose), narrow the procedure accordingly.
