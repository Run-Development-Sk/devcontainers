---
name: run-integrate-devcontainer-addon
description: >-
  Integrate a devcontainer add-on (a template or feature folder from
  https://github.com/RunDevelopmentSk/devcontainers, e.g. `templates/odoo-19`,
  `features/ai-agents`) into the current project: apply the instructions of its copied-in
  `.devcontainer/<add-on>.md` descriptor and reconcile project files the raw copy
  overwrote; with a clean working tree, first offers to fetch and copy the add-on.
  Use for "integrate add-on", "add devcontainer add-on", "apply devcontainer
  feature", "wire in the copied add-on".
---

# run-integrate-devcontainer-addon

Skill for finishing the manual step of "copy a template or feature folder from
[RunDevelopmentSk/devcontainers](https://github.com/RunDevelopmentSk/devcontainers) into a
project" - it reads the add-on's own `.devcontainer/<add-on>.md` instructions and applies them,
and reconciles any project file the raw copy overwrote so project-specific content is not lost.

## When to use

- "integrate add-on", "add devcontainer add-on", "integrate `templates/odoo-19`/`features/ai-agents`/`features/ai-agents-speckit`/`features/ai-agents-superpowers`/... into this project", "apply devcontainer feature", "wire in the copied add-on",
- the entry point is also the command `/run.integrate-devcontainer-addon`.

## Add-on shape (context)

The source repo has two top-level categories: `templates/<name>` - a complete, standalone
devcontainer base (e.g. `templates/odoo-19`, `templates/php-7.3_mysql-5.7`) - and
`features/<name>` - an add-on merged into an existing devcontainer (e.g. `features/ai-agents`,
`features/ai-agents-speckit`, `features/ai-agents-superpowers`); excluding dotfiles and `docs`/`tmp`.
Each such folder (one level under `templates/` or `features/`) is one add-on. Consumers
integrate it by copying the folder's _contents_ into their project root, which lands a
`.devcontainer/<add-on>.md` descriptor at the project's `.devcontainer/` path alongside
whatever other files the add-on ships.

A descriptor with real integration instructions has an `## Installation` section, typically:
"copy the contents of the `<add-on>` folder into the project folder", then optional
"add the following to the end of `<script>`" / "add the following to `.gitignore`" snippets,
then "rebuild the devcontainer"; often followed by a `## Removal` section. A plain one-line
`.devcontainer/<name>.md` with no headings (e.g. `ubuntu-noble.md`) is a devcontainer
_identification_ stub, not an add-on descriptor - ignore those.

A feature folder may also ship a **nested technology-specific folder** named after one of the
templates (e.g. `features/ai-agents/odoo-19`) - extra content for that feature that only applies
when it is combined with the matching template (e.g. `templates/odoo-19`). This nested folder
comes along with the raw copy of the feature's contents; see step 4 for how to handle it.

## 1. Determine mode

Run `git status --porcelain` (repo root).

- **Empty (no pending changes)** -> **fetch mode**: go to step 2.
- **Non-empty** -> **integration mode**: treat the full set of pending changes as the raw
  add-on copy that is waiting to be reconciled; go to step 3.

## 2. Fetch mode - ask, download, copy

1. Ask the user which add-on to integrate (list the immediate subfolders of `templates/` and
   `features/` in
   [RunDevelopmentSk/devcontainers](https://github.com/RunDevelopmentSk/devcontainers) as
   candidates if known, otherwise fetch both category listings first; present candidates with
   their category prefix, e.g. `templates/odoo-19` or `features/ai-agents`).
2. Clone the source repo shallowly into a temporary directory outside the project (e.g.
   `git clone --depth 1 https://github.com/RunDevelopmentSk/devcontainers <tmp-dir>`).
3. Copy the chosen add-on folder's _contents_ (not the folder itself) into the project root,
   exactly like a manual copy would (this reproduces the overwrite the add-on's own
   `## Installation` section describes).
4. Remove the temporary clone.
5. Continue at step 3 (the copy just performed is now the pending change set for integration
   mode) - re-run `git status --porcelain` to see it.

## 3. Locate and read the add-on descriptor

Among the pending changes (`git status --porcelain`), find the `.devcontainer/<add-on>.md`
file(s) that are new or modified and qualify as an add-on descriptor (see "Add-on shape"
above).

- **None found**: report that no add-on descriptor is present in the pending changes and ask
  the user to point to it, or confirm this isn't an add-on integration - do not guess.
- **More than one found**: ask the user which one to process (or process them one at a time,
  confirming between each), since installation steps from different add-ons can otherwise get
  mixed up.

Read the descriptor fully before acting - it is the source of truth for what this specific
add-on needs (script names and snippets, `.gitignore` entries, and any notes/limitations
vary per add-on; do not assume the shape of a previously-seen add-on applies here).

## 4. Apply the descriptor's instructions

Follow the `## Installation` section (or equivalently named instructions) step by step:

- the "copy the contents of the `<add-on>` folder" step is already done (that's the pending
  change set) - skip it,
- for "add the following to the end of `<file>`" steps, append the given snippet to that file
  if it is not already present (check first - do not duplicate it if the file already has it,
  e.g. from a previous run or a prior integration),
- for "add the following to `.gitignore`" steps, append the given lines the same way,
  idempotently,
- leave "rebuild the devcontainer" and similar user-side actions for the user to perform - do
  not attempt to run them,
- if the descriptor has a `## Known limitation` or similar note, keep it in mind for the final
  summary but do not act on it beyond what it explicitly instructs,
- if the raw copy included a nested technology-specific folder named after a template (e.g.
  `odoo-19/` inside a `features/ai-agents` copy) and the project is actually based on that
  template, merge that folder's contents into the project root (same reconciliation rules as
  step 5 below applies to any file it overwrites) and then delete the now-empty nested folder;
  if the project is not based on that template, or it is unclear, leave the folder in place and
  ask the user whether to merge or delete it - do not silently drop it,
- every rule (`.agents/rules/*.md`) the add-on adds - including rules from a merged nested
  folder - must be referenced in `AGENTS.md` per the DoD of the `run-add-agent-asset` skill
  (`.agents/skills/run-add-agent-asset/SKILL.md`); add a missing reference idempotently.

## 5. Reconcile files the copy overwrote

For every file in the pending change set that **existed before** the copy (i.e. it is a
modification of a tracked file, not a new file):

1. Get the previous content: `git show HEAD:<file>`.
2. Get the new content: the working-tree version (the raw add-on copy).
3. Diff the two (`git diff HEAD -- <file>`) and read both versions.
4. Decide, content block by content block:
   - content that is in the **old** version but missing from the **new** one, and is
     **project-specific** (not something the add-on itself owns or manages) -> restore it into
     the final version,
   - content that is in the **new** version and is genuinely **new material introduced by the
     add-on** (not just the add-on's already-known boilerplate replacing itself) -> keep/merge
     it into the final version,
   - content that is unchanged, or that is the add-on updating its own previously-added
     material -> keep the new version as-is.
5. Write the reconciled result back to the file (replacing the raw overwrite) so the final
   file is neither "old project content losing the add-on's update" nor "add-on content losing
   project-specific material", but both combined.
6. If it is not clear whether a piece of content is project-specific or add-on-owned, do not
   silently pick one - leave the safer option (usually: keep both, or keep the new version) and
   flag the spot explicitly in the final summary as a question for the user.

Files that are **new** (untracked, no previous committed version) need no reconciliation - they
are simply new add-on files; note them in the summary.

Placeholder entries (`<@todo:...>`) of the "Rules applicable on demand" section in `AGENTS.md`
are not carried over into a project that has no on-demand rules - omit the section there instead
of leaving unfilled placeholders.

## 6. Align existing agent artifacts

If the project has the `run-add-agent-asset` skill after the integration
(`.agents/skills/run-add-agent-asset/SKILL.md`), bring the project's pre-existing agent
artifacts - rules, commands, skills, and subagents, including those in agent-specific locations
(`.claude/*`, `.augment/*`, `.codex/*`) - into line with that skill (location, naming,
frontmatter, `AGENTS.md` registration, subagent formats). That skill is the source of truth for
the target shape; vendor-provided artifacts keep their names as it prescribes. Update references
to every moved or renamed artifact, and ask the user when it is unclear whether an artifact is
project-owned or vendor-provided.

## 7. Summary and open questions

End with:

- what was applied from the descriptor's instructions (script hooks appended, `.gitignore`
  entries appended, ...),
- which pre-existing files were reconciled, and for each: what project-specific content was
  restored and what new add-on content was merged in,
- which files are newly added by the add-on,
- which rules were registered in `AGENTS.md`,
- which pre-existing agent artifacts were aligned with the `run-add-agent-asset` skill, and how
  (moved, renamed, frontmatter or `AGENTS.md` registration fixed),
- whether a nested technology-specific folder was found, and what was done with it (merged and
  deleted, or left in place pending the user's decision),
- any spot the skill was not confident about, as direct questions to the user,
- a reminder that nothing was committed/staged and rebuilding the devcontainer (if applicable)
  is up to the user.

## Hard Rules

- **Never commit, stage, unstage, or otherwise change git state** (`git add`, `git commit`,
  `git restore`, `git reset`, ...) - this skill only edits working-tree files; leave everything
  else to the user.
- Do not silently discard project-specific content on the assumption an overwrite is "probably
  fine" - reconcile per step 5, and ask when genuinely unsure rather than guessing.
- Do not attempt to rebuild the devcontainer or run other environment-changing commands the
  descriptor lists as user steps.
- Never print secret values while reading scripts/config the add-on touches
  (`.agents/rules/run.secret-safety.md`).
- Follow the language policy for anything written into project files
  (`.agents/rules/run.language-policy.md`).

## Related

- `.agents/commands/run.integrate-devcontainer-addon.md` - paired command
  `/run.integrate-devcontainer-addon` (entry point to this skill).
- `docs/ai-agents.md` - source of truth on this project's own unified agent configuration (the
  `features/ai-agents` add-on's target shape when integrating it into a project).
- `.agents/skills/run-remove-devcontainer-addon/SKILL.md` - the inverse operation (uninstalling
  an add-on).
- `.agents/skills/run-add-agent-asset/SKILL.md` - target shape of agent artifacts and their
  `AGENTS.md` registration.
- `.agents/rules/run.secret-safety.md`, `.agents/rules/run.language-policy.md`.
