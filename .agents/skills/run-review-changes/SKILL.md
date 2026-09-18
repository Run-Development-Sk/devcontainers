---
name: run-review-changes
description: >-
  Review changes made by an AI agent - staged files, specific commit(s), or branch
  changes against main - and report remarks only (read-only, no edits/commits).
  Source code gets a proper code review; non-code changes are checked for correctness
  and completeness against the original request. Use for "review changes", "review
  staged files", "review commit <hash>", "review branch changes", "PR review".
---

# run-review-changes

Skill for reviewing/revising a set of changes that an AI agent already made - **a read-only
review**: the agent only writes remarks, and never edits, stages, unstages, or commits
anything.

## When to use

- "review changes", "changes review", "revise the changes", "review staged files", "review commit `<hash>`", "review branch changes against main", "review branch", "PR review", "review PR",
- the entry point is also the command `/run.review-changes`.

## Input

Two things must be known before the review starts. If the user already specified them in the
request, do not ask again - otherwise ask now (can be combined into a single question):

1. **Source of changes** - one of:
   - **staged files** (`git diff --cached`),
   - **commit hash(es)** to review (single hash, a range, or a list of discrete hashes), or
   - **branch changes** against another branch (usually `main`, using `git diff main...` or `git diff main...HEAD`).
2. **Original request/prompt** that led to the changes (the instruction that was given to the
   AI agent whose output is being reviewed) - needed to judge correctness of non-code changes
   and the completeness of the whole change set.

## 1. Determine the diff to review

- **Staged files**: `git status --porcelain` (staged entries) + `git diff --cached` for the
  full content diff; `git diff --cached --stat` for a quick file overview.
- **Commit hash(es)**:
  - single hash -> `git show <hash>`,
  - contiguous range -> `git diff <hash1>^..<hash2>` (or `git log --oneline <hash1>..<hash2>` +
    per-commit `git show`),
  - discrete/non-contiguous list -> review each commit separately with `git show <hash>` and
    report findings per commit,
  - if it is unclear whether the given hashes form a range or a discrete list, ask the user.
- **Branch changes** (Pull Request code review):
  - branch changes against `main` (or another target branch if specified) -> `git diff main...HEAD` (or `git diff main...` or specifying another base like `git diff target_branch...HEAD`) to view all changes introduced in the current branch since it branched from `main`.
  - `git log main..HEAD --oneline` to see the commits included in the review.
- Never modify the working tree/index while inspecting the diff (no `git add`, `git checkout`,
  `git commit`, `git reset`, `git restore`, etc.).
- **Nothing to review**: if staged mode has no staged files, commit mode has an invalid/unreachable hash, or branch mode has no differences from `main`, report it and stop - do not fall back to an unrelated diff.

## 2. Classify each changed file

For every changed file, decide whether it is **source code** (programming-language files,
scripts, infrastructure-as-code, build/CI configuration with executable logic, SQL migrations,
etc.) or **not source code** (documentation, prose, prompts/instructions, plain data, generic
non-executable configuration, assets, ...). Mixed change sets are normal - classify per file,
not per change set as a whole.

## 3. Review source-code files (code review)

For each source-code file, identify its language/technology (by extension, shebang, or content)
and review it the way that type is best reviewed, e.g.:

- **correctness** - logic errors, edge cases, off-by-one, null/undefined handling, race
  conditions,
- **architecture & design** - separation of concerns, appropriate abstraction level, consistency
  with the existing codebase's patterns and conventions, no unnecessary coupling,
- **language/framework idioms** - does it follow the identified language's/framework's
  established conventions and best practices (e.g. idiomatic error handling in Go,
  PEP 8/typing in Python, correct async/await usage in JS/TS, layer caching and minimal images
  in a Dockerfile, quoting and `set -euo pipefail` in shell scripts, idempotency in IaC,
  parameterized queries in SQL, ...),
- **security** - injection, unsafe deserialization, secrets in code, unsafe permissions, missing
  input validation at trust boundaries,
- **performance** - obvious inefficiencies, unnecessary work in hot paths,
- **error handling & robustness** - swallowed errors, missing cleanup, unclear failure modes,
- **readability & maintainability** - naming, duplication, dead code, overly complex
  constructs,
- **tests** - are the changes covered by tests where the codebase's convention expects it.

Use the codebase's own conventions (linters, style guides, existing patterns,
`AGENTS.md`/`CLAUDE.md` if present) as the baseline for what "consistent" means in that
project.

## 4. Review non-source-code files (against the original request)

For each non-code file, evaluate the change strictly against the **original request/prompt**
obtained in the Input step:

- **correctness** - does the change do what was asked,
- **completeness** - is anything from the request missing or only partially done,
- **side effects** - did it change something the request did not ask for,
- **consistency** - does it align with related project conventions/instructions where relevant.

## 5. Report remarks

Output **remarks only**, grouped by file (and, for multiple commits, sub-grouped by commit).
For each remark include: its number, its severity label, the file (and line/section if
applicable), a short description of the issue, and why it matters. If a file/commit has no
remarks, say so briefly rather than omitting it. End with a short overall summary of whether
the change set as a whole fulfills the original request.

**Numbering**: number the remarks with a single continuous sequence starting at `1` and
increasing by one, running across all files, commits, groups, and topics - never restart the
count in a new group. The number is the remark's unique identifier in the follow-up
conversation about fixing the remarks ("fix 3 and 7"), so it comes first in the remark and is
never reused or reassigned within one report:

```
1. [Blocking] path/to/file.py:42 - <description>
2. [Minor] path/to/other-file.md - <description>
```

Where the overall summary (or any other part of the report) refers to a remark, reference it by
its number instead of restating it.

**Severity**: every remark carries exactly one severity label, placed right after its number -
`[Blocking]`, `[Minor]`, or `[Suggestion]`. Do not introduce a different or finer-grained scale
unless the user asks for one.

## Hard Rules

- **Read-only**: never edit, add, remove, stage, unstage, or commit anything - not the reviewed
  files, not any other file.
- Only output findings/remarks as text - no code fixes are applied, even if the fix is obvious.
- Do not skip the Input step - both the change source and the original request must be known
  before reviewing (ask if not already given).
- Never quote secrets found in the diff verbatim in the report
  (`.agents/rules/run.secret-safety.md`) - reference their location instead.

## Related

- `.agents/commands/run.review-changes.md` - paired command `/run.review-changes` (entry point
  to this skill).
- `docs/ai-agents.md` - source of truth on unified agent configuration.
- `.agents/rules/run.secret-safety.md` - no secrets in reports.
