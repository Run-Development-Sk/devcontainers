---
name: run-remove-devcontainer-addon
description: >-
  Remove a previously integrated devcontainer add-on (a template or feature folder from
  https://github.com/RunDevelopmentSk/devcontainers) from the current project, following
  the `## Removal` instructions in its `.devcontainer/<add-on>.md` descriptor; accepts the
  add-on name as an argument, otherwise lists the integrated add-ons and asks. Builds a
  removal plan and asks for explicit confirmation before deleting anything. Use for
  "remove add-on", "uninstall devcontainer add-on", "undo devcontainer feature".
---

# run-remove-devcontainer-addon

Skill for reversing a devcontainer add-on integration performed via the
`run-integrate-devcontainer-addon` skill (or manually), by following the add-on's own
`## Removal` instructions in `.devcontainer/<add-on>.md`.

## When to use

- "remove add-on", "uninstall devcontainer add-on", "remove `templates/odoo-19`/`features/ai-agents`/`features/ai-agents-speckit`/`features/ai-agents-superpowers`/... from this project", "undo devcontainer feature",
- invoked directly as `/run-remove-devcontainer-addon` in Claude Code; Codex and Auggie use the skill natively.

## Input

An add-on name, optionally as an argument to the command/skill:

- accepted forms: `<add-on>` (e.g. `ai-agents-speckit`) or `<add-on>.md` (e.g.
  `ai-agents-speckit.md`) or a path to it (e.g. `.devcontainer/ai-agents-speckit.md`) - normalize by
  stripping any directory prefix and a trailing `.md` suffix to get the bare add-on name,
- **no argument given**: list the add-ons currently integrated in the project - scan
  `.devcontainer/*.md` for descriptors that have a `## Removal` section (plain one-line
  identification stubs like `ubuntu-noble.md` have no such section and are not removable
  add-ons - skip those) - and ask the user to pick one from the list.

## 1. Locate and read the descriptor

Resolve to `.devcontainer/<add-on>.md`. If it does not exist in the project, report that this
add-on is not integrated here and stop - do not guess an alternative.

Read the full file, both the `## Installation` section (it defines what "everything that was
added" in the Removal section actually refers to: which folder was copied in, which snippets
were appended to which files, which `.gitignore` lines were added) and the `## Removal` section
itself (it may add extra steps beyond "delete everything that was added", e.g. restoring a
symlink that installation replaced with a materialized copy).

## 2. Build the removal plan

Determine, as concretely as possible, what this add-on's integration touched:

- **Copied-in files/folders**: to find the exact set, look at project git history for the
  commit(s) that introduced `.devcontainer/<add-on>.md` (e.g.
  `git log --follow --diff-filter=A -- .devcontainer/<add-on>.md`) and inspect that commit's
  file list (`git show --stat <commit>`) as the baseline set of files the add-on added. Files
  from that set that were later merged/reconciled with project-specific content (see the
  `run-integrate-devcontainer-addon` skill) need care in step 3, not blind deletion. If history does
  not clearly show this (e.g. the add-on was integrated without ever being committed), fall back
  to the Installation section's own description of what was copied and ask the user to confirm
  the file list before proceeding.
- **Appended snippets**: the exact snippet text the Installation section says to add to specific
  files (scripts, `.gitignore`, ...) - locate that exact block in the current file content.
- **Removal-section-specific steps**: anything explicitly listed there beyond "delete everything
  that was added" (e.g. `ln -s ...` to restore a symlink, cleaning up now-untracked generated
  files after a `.gitignore` change, ...).

Distinguish, for every file touched by the add-on, whether it is **wholly owned by the add-on**
(safe to delete outright) or **shared with project-specific content** (only the add-on's own
block/snippet should be stripped, the rest of the file must be preserved) - do not delete a
shared file outright just because the add-on touched it.

## 3. Confirm before changing anything

Present the full plan to the user - files/folders to delete, snippets to remove and from which
files, symlinks or other steps to restore - and get explicit confirmation before applying it.
Deleting untracked files is not recoverable via git, so do not skip this step even in an
otherwise autonomous session.

## 4. Apply the plan

On confirmation:

- delete files/folders that are wholly add-on-owned,
- strip the add-on's appended snippet/lines from shared files, leaving the rest of the file
  (including any project-specific content, restored or added there by the
  `run-integrate-devcontainer-addon` skill or manually) untouched,
- perform Removal-section-specific steps (e.g. recreate a symlink),
- leave "rebuild the devcontainer" and other user-side actions for the user - do not attempt to
  run them.

Use plain filesystem operations (delete/edit), not `git rm` - the change should show up as a
normal working-tree diff for the user to review, per the Hard Rules below.

## 5. Summary and open questions

End with: what was deleted, what was stripped from which shared files (and what was left
intact there), which Removal-section steps were performed, any manual follow-up left for the
user (e.g. rebuild the devcontainer), and any spot the skill was not confident about as a direct
question.

## Hard Rules

- **Never commit, stage, unstage, or otherwise change git state** (`git add`, `git commit`,
  `git rm`, `git restore`, `git reset`, ...) - only edit/delete working-tree files; leave
  everything else to the user.
- **Never delete or overwrite anything without the confirmation step (3)** - the removal plan
  must be shown and confirmed first.
- Never delete a file that mixes add-on and project-specific content outright - strip only the
  add-on's own contribution per step 2/4.
- Do not attempt to rebuild the devcontainer or run other environment-changing commands the
  descriptor lists as user steps.
- Never print secret values while reading scripts/config the add-on touches
  (`.agents/rules/run.secret-safety.md`).

## Related

- `.agents/skills/run-integrate-devcontainer-addon/SKILL.md` - the inverse operation; also the
  best source for how a given add-on's integration merged project-specific content into shared
  files.
- `.agents/rules/run.secret-safety.md`.
