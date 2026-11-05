# Instructions for AI agents

This file is a **shared source of truth** for the AI agents in the project
(Claude Code, Codex, Auggie). Codex and Auggie read it natively; Claude Code reads it
through `CLAUDE.md`, which imports it.

Configuration details of individual agents and the unified structure are in
`docs/ai-agents.md`.

Before working, check:

- `.agents/rules/*.md` – modular workspace rules

## Always applicable cross-cutting rules

- @.agents/rules/run.language-policy.md
- @.agents/rules/run.secret-safety.md
- @.agents/rules/run.dry-kiss-yagni-but-scalable.md
- @.agents/rules/run.explicit-change-only.md
- @.agents/rules/run.timeless-comments.md

## General description

The current project contains devcontainers that can be used in other projects as development environments for a given technology. It has two top-level categories:

- `templates/` – complete, standalone devcontainer bases (e.g. `templates/odoo-19`, `templates/php-7.3_mysql-5.7`). Individual templates are independent, although sometimes quite similar, as they only update a given technology for its newer version.
- `features/` – add-ons merged into an existing devcontainer (e.g. `features/ai-agents`, `features/ai-agents-speckit`, `features/ai-agents-superpowers`).
