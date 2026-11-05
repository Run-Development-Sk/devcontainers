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

## Rules applicable on demand

Read the matching rule before working on:

- <@todo:action-or-area-description> (`<@todo:path-to-scope-files>`) – `.agents/rules/run.<@todo:name>.md`
- ...

## General description

The current project is built on <@todo:tech-stack-description>. Functional code is located in the directories <@todo:path-to-project-src>.

It is a <@todo:project-type> project.

The analysis is in the file <@todo:project-analysis-file>.

The main development strategy is to avoid programming as much as possible and instead use existing <@todo:tech-stack-description> modules and their configuration. Where this is not possible, the required functionality is added either in the form of a custom or vendor module.

## Misc

<@todo:misc-section>
