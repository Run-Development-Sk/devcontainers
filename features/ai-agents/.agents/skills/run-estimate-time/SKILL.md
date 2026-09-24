---
name: run-estimate-time
description: >-
  Estimate the time of a task given by a prompt against the project's source code (read-only):
  break it into steps, give each a human-only and an AI-assisted estimate, sum them, and propose
  overhead (communication, analysis, code review, testing, deployment, contingency). Use for
  "estimate time", "time estimate", "how long will it take", "odhad času", "cenová ponuka".
---

# run-estimate-time

Skill for a **read-only** time estimate of a task: the agent only answers in chat, never edits,
creates, or commits anything. To keep the estimate, use `/run.save-response`.

## When to use

- "estimate time", "time estimate", "how long will it take", "odhad času", "koľko to bude trvať", "cenová ponuka",
- the entry point is also the command `/run.estimate-time`.

## Definitions

- **Human time** `[<n>h]` - time of a developer who knows both the project and its technology
  stack, working without AI.
- **AI time** `[ai:<n>h]` - development time accelerated by AI: the time the human spends
  prompting, reviewing, fixing, and verifying the AI's output (not the agent's run time).
- The developer's continuous testing while working is part of development, not a testing item.
- **Number format** - rounded **up** to 0.25 h, written without leading or trailing zeros:
  `[0.25h]`, `[1h]`, `[1.5h]`, `[ai:0.75h]`, `[ai:11.5h]`. No space after `ai:`.
- **Subtotals and the total** (section, implementation, overall) are written without brackets:
  `6.5h ai:2.75h`.

## Configuration

The tables below are the tunable defaults; adjust them here to calibrate all future estimates.
Where a range is given, pick a value within it and let the chosen value follow from the task
(size, risk, analogous existing code).

### AI speedup by type of work (human time ÷ AI time)

| Type of work                                                                                | Speedup    |
| ------------------------------------------------------------------------------------------- | ---------- |
| boilerplate, CRUD, automated tests, documentation                                           | 2 – 4×     |
| common logic in known code                                                                  | 1.5 – 2×   |
| debugging, legacy code, undocumented external systems/integrations, pixel-precise UI tuning | 1.3 – 1.7× |

### Overhead

The base "impl." is the **human** implementation subtotal - items AI does not speed up must come
out equal in both columns.

| Item                                           | Human                         | AI                    |
| ---------------------------------------------- | ----------------------------- | --------------------- |
| Client communication                           | 10 % of impl.                 | = human               |
| Analysis / specification                       | 10 – 15 % of impl.            | 60 % of human         |
| Code review (with `run-review-changes` for AI) | 10 % of impl.                 | 50 % of human         |
| Manual testing (dedicated tester)              | 15 – 20 % of impl.            | = human               |
| Unit tests                                     | 20 – 30 % of impl.            | 40 % of human         |
| E2E tests                                      | 15 – 25 % of impl.            | 50 % of human         |
| Production deployment                          | 0.25 – 1 h (lower with CI/CD) | = human               |
| Contingency                                    | 15 – 30 % of human subtotal   | same % of AI subtotal |

- An AI value given as "% of human" is computed from the already rounded human value of the same
  item.
- A testing item gets a time only when confirmed in step 1; an unconfirmed one is still listed,
  without a time, as not included, so the estimate keeps the reminder to consider it.
- Contingency is taken from the subtotal of implementation + all other overhead items; its
  percentage grows with the number and weight of the risk-flagged steps.

## 1. Input

- The task comes from the argument/prompt; if missing, ask for it.
- Ask only about points that substantially affect the estimate and that neither the prompt nor
  the code (step 2) answers - in **one combined question** with at most 3–5 targeted points. With
  no such point, estimate right away without asking.
- **Testing scope** (manual testing by a dedicated tester, unit tests, E2E tests) is confirmed by
  the prompt or by an answer; when the prompt is silent on it, add it to the question only if one
  is being asked anyway. Otherwise assume the automated test types the project already uses and
  treat the rest as unconfirmed.
- Everything else that stays unclear becomes an explicit **assumption** - do not block the
  estimate on it.

## 2. Locate and inspect the source code (read-only)

- **Project-management project**: if `docs/pm-project-info.md` exists, the estimated project's
  source code is at the path given by its `**PM_PROJECT_PATH:**` line (a relative path resolves
  against the current project root). If the line is missing or the path does not exist, tell the
  user and ask for the path.
- Otherwise the source code is the current project.
- Identify the stack, the modules/files the task touches, existing tests and their conventions,
  CI/CD and deployment setup, and similar already implemented features usable as an analogy.
  Ground the estimates in these findings; if there is no relevant code (greenfield), say so.

## 3. Break the task down

- Split the task into meaningful, verifiable steps grouped into sections (e.g. Backend,
  Frontend, Data migration).
- A step takes 0.25 h to ~4 h of human time; split anything bigger.
- Give each step both estimates, choosing the AI time by the speedup table.
- Give each section a subtotal - the sum of its steps, separately for human and AI time.
- Mark a risky step with `⚠ risk: <short reason>`.

## 4. Sum and add overhead

- The implementation subtotal is the sum of the already rounded step values, separately for
  human and AI time.
- Compute the overhead items by the Overhead table, round each up to 0.25 h, and label the
  section as a proposal to be adjusted to the project.
- The total is implementation subtotal + overhead, separately for human and AI time.

## 5. Output

Write in the language of the user's prompt (translate the headings). Estimates stand directly at
the end of the line, without alignment:

```
## Assumptions
- Manual testing and unit tests confirmed, no E2E tests
- …
## Out of scope
- …

## Implementation
### Backend 5h ai:2.25h
1. Model `sale.commission` + migration [2h] [ai:0.75h]
2. Commission calculation on order confirmation [3h] [ai:1.5h] ⚠ risk: unclear discount rules
### Frontend 1.5h ai:0.5h
3. Commission form and list [1.5h] [ai:0.5h]

Implementation subtotal: 6.5h ai:2.75h

## Overhead (proposal – adjust to the project)
- Client communication [0.75h] [ai:0.75h]
- Analysis [1h] [ai:0.75h]
- Code review [0.75h] [ai:0.5h]
- Manual testing [1h] [ai:1h]
- Unit tests [1.5h] [ai:0.75h]
- E2E tests – not included (not confirmed), consider adding
- Production deployment [0.5h] [ai:0.5h]
- Contingency (20 %) [2.5h] [ai:1.5h]

## Total 14.5h ai:8.5h

## Open questions
- …
```

End with a one-line note: for an important quote it is worth running this skill in an
independent agent and comparing both estimates with `/run.compare-agent-outputs`.

## Hard Rules

- **Read-only**: never edit, create, delete, stage, or commit anything - in this project or in
  the estimated one.
- Never quote secrets found in the code (`.agents/rules/run.secret-safety.md`).

## Related

- `.agents/commands/run.estimate-time.md` - paired command `/run.estimate-time` (entry point to
  this skill).
- `.agents/skills/run-review-changes/` - AI-assisted code review assumed by the Code review item.
- `.agents/skills/run-compare-agent-outputs/` - comparison of independent estimates.
