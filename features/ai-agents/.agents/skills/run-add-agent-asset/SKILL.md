---
name: run-add-agent-asset
description: >-
  Adding and modifying agent artifacts (skills, rules, slash commands,
  subagents) in accordance with the unified configuration of AI agents described in
  docs/ai-agents.md. Use when "create/edit skill | rule | command | subagent",
  "add agent artifact".
---

# run-add-agent-asset

Skill for safely adding new agent artifacts so that they work across all agents (Auggie, Claude Code, Antigravity, Codex).
**The source of truth is `docs/ai-agents.md`** – this skill is only a procedure and checklist; do not duplicate symlink or format details, refer to it instead.

## When to use

- "create/edit skill", "add rule", "new slash command", "new subagent",
- "add agent artifact" / "modify agent configuration".

## 1. Determine artifact type

- **rule** – always/frequently valid guardrails (`.agents/rules/run.<name>.md`),
- **skill** – repeatable procedure/workflow (`.agents/skills/run-<name>/SKILL.md`),
- **command** – short entry point `/run.<name>` (`.agents/commands/run.<name>.md`),
- **subagent** – isolated specialist with its own prompt (`.agents/agents/run.<name>.*`).

If it is not a new type of artifact, **new symlinks are not needed** – existing ones in `docs/ai-agents.md` already ensure cross-tool discovery.

## 2. Conventions

- **namespace prefix** – all local/shared/project-owned artifacts (rules, commands, skills, subagents) are namespaced with `run.` / `run-` to mark them as project-owned and avoid collisions with third-party or vendor-provided artifacts (e.g. `speckit-*`, which stay unprefixed and must never be renamed); use `run.<name>` for commands/rules/subagents (files) and `run-<name>` for skill directories,
- kebab-case for the part of the name after the prefix (e.g., `run.deploy-staging`, `run-review-pr`),
- avoid double-prefixing (`run.run.<name>`, `run-run-<name>`) – if a requested name already carries a `run.` or `run-` prefix, strip that prefix first and then apply the correct prefix for the artifact type (`run.` for command/rule/subagent files, `run-` for skill directories),
- content and `description` **in English**,
- **plain file paths** – write paths as plain code spans (`docs/ai-agents.md`, `.agents/rules/run.<name>.md`), never as Markdown links (`[...](...)`) – the link target duplicates the path and does not help an AI agent,
- **context economy** – size an artifact by when it is loaded, not by how much there is to say:
  - **always in context** (every session, every agent): always-apply rule bodies, `AGENTS.md`, and the `description` of every skill, command, and subagent – keep these minimal and free of motivational prose or content restated elsewhere (e.g. do not repeat the `description` in the body),
  - skill/subagent `description` drives activation (`agent_requested` / `model_decision`) and delegation – 2–4 lines: what it does + trigger phrases; procedure details belong in the body, which loads only on activation,
  - command `description` is not used for model activation (commands are user-invoked) – one line in the form "Entry point to the `run-<name>` skill – <what it does>",
  - bodies of on-demand rules, skills, commands, and subagents load only on use – completeness there costs nothing per session; prefer an on-demand rule (`agent_requested` / `model_decision` / `glob`) for guidance that applies only to a specific kind of work or area of the code, while guidance for everything inside a single subdirectory belongs in a nested `AGENTS.md` in that subdirectory (see `docs/ai-agents.md`).

## 3. Cookbook by type

### Rule (`.agents/rules/run.<name>.md`)

- Combined frontmatter: `description` + `type:` (Auggie: `always_apply|agent_requested`, `manual` is skipped by CLI – only works in IDE extensions) + `trigger:` (Antigravity: `always_on|glob|model_decision|manual`). Unknown keys are ignored by each agent.
- Codex has no rules folder, and Claude Code's native `.claude/rules/` is not wired into this setup -> make the rule available to them via `AGENTS.md`:
  - `always_apply|always_on` rule – a `@.agents/rules/run.<name>.md` import (its body is loaded into every session),
  - `agent_requested|model_decision|glob` rule – a plain path reference without `@` (the body is read only when needed) in the form `- <area> (<scope paths>) – .agents/rules/run.<name>.md`; the parenthesized scope paths are optional (for a `glob` rule, list its `globs:`), all paths are written as code spans.

### Skill (`.agents/skills/run-<name>/SKILL.md`)

- Directory + `SKILL.md` with **mandatory** frontmatter `name` (= `run-<name>`) and `description`.
- Optional subdirectories `scripts/`, `references/`, `assets/`.
- No registration is needed elsewhere – agents auto-discover skills.

### Command (`.agents/commands/run.<name>.md`)

- File `run.<name>.md` -> `/run.<name>`; an additional subdirectory adds a further namespace (`frontend/run.component.md` -> `/frontend:run.component`).
- Frontmatter with a `description` field (folded scalar, e.g., `description: >-`).
- **Codex** does not support slash commands – use the corresponding skill directly there; the command should be a thin entry point referencing the skill.

### Subagent (`.agents/agents/`)

- Add **both** formats for the same agent, sharing the `run.<name>` base name:
  - `run.<name>.md` (Claude Code, Auggie): YAML frontmatter `name`, `description`, optionally `color` (Auggie), `tools`, `model` (Claude); body = system prompt,
  - `run.<name>.toml` (Codex): `name`, `description`, `developer_instructions` (system prompt), optionally `model`, `sandbox_mode`.
- Antigravity does not support file-based subagents yet (only `define_subagent` at runtime) – do not edit anything extra for it.

## 4. Documentation and Registry Sync (DoD)

- new **always-apply rule** -> add to the list of "Always applicable cross-cutting rules" in `AGENTS.md` and add a `@`-import,
- new **on-demand rule** (`agent_requested` / `model_decision` / `glob`) -> add a plain path reference to the list of "Rules applicable on demand" in `AGENTS.md` (never a `@`-import; create the section right after "Always applicable cross-cutting rules" with the lead-in "Read the matching rule before working on:" if it does not exist yet),
- **new type of artifact/agent requiring a new symlink** -> add a line to the symlink table **and** to the `ln -s` block in `docs/ai-agents.md`,
- if a new command/skill was created that is an entry point to another, link them with a reference and matching names (e.g., command `/run.<name>` <-> skill `run-<name>`).

## 5. Verification Checklist (cross-tool)

After creation, verify that the artifact is visible to each relevant agent:

- **Auggie** – skills and subagents natively from `.agents/skills` / `.agents/agents`; commands via the `.claude/commands` compatibility fallback; rules via the materialized `.augment/rules` directory (temporary workaround in `docs/ai-agents.md` – reopen the devcontainer after editing rules),
- **Claude Code** – commands/skills/subagents via `.claude/*` symlinks; rules only via `AGENTS.md` (see §3 Rule),
- **Antigravity** – rules and skills natively from `.agents/*`; does not support commands in the CLI; does not read subagents from files,
- **Codex** – `.agents/skills` and `AGENTS.md` natively; subagents from `.codex/agents` (`.toml`) via symlink; does not support commands; rules only via `AGENTS.md` (see §3 Rule; it does not expand `@`-imports, see `docs/ai-agents.md`).

## Related

- `docs/ai-agents.md` – **source of truth** about unified configuration and symlinks.
- `.agents/rules/run.secret-safety.md` – never include secrets in artifacts – neither in files nor in prompts.
- `.agents/commands/run.add-agent-asset.md` – paired command `/run.add-agent-asset` (entry point to this skill).
