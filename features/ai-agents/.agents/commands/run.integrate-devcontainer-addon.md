---
description: >-
  Entry point to the run-integrate-devcontainer-addon skill – integrate a copied-in
  devcontainer add-on and reconcile project files the copy overwrote.
---

# /run.integrate-devcontainer-addon – Integrate a devcontainer add-on

Follow the procedure according to the **`run-integrate-devcontainer-addon`** skill
(`.agents/skills/run-integrate-devcontainer-addon/SKILL.md`). The command and the skill have
the same output; this command is the entry point for Claude Code, Auggie, and Antigravity.
(Codex does not support slash commands – use the `run-integrate-devcontainer-addon` skill
directly there.)

In short (details in the skill):

1. If the working tree has no pending changes, ask which add-on to integrate, fetch it from
   the source repo, and copy it into the project.
2. Otherwise, find the `.devcontainer/<add-on>.md` descriptor among the pending changes and
   follow its installation instructions (script hooks, `.gitignore` entries, ...), and register
   any rules it adds in `AGENTS.md`.
3. For any pre-existing project file the copy overwrote, reconcile it against the previous
   committed version: restore project-specific content the overwrite dropped, and merge in
   genuinely new add-on content instead of leaving the raw overwrite in place.
4. Align pre-existing agent artifacts (rules, commands, skills, subagents) with the
   `run-add-agent-asset` skill.
5. Report a summary of what was integrated/reconciled, and ask about any ambiguous spots.

Hard rule: never commit, stage, unstage, or otherwise change git state – this only edits
working-tree files, and rebuilding the devcontainer is left to the user.

If the user already named the add-on, do not ask again – proceed with that add-on.
