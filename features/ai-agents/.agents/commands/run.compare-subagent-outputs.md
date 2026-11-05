---
description: >-
  Entry point to the run.compare-subagent-outputs subagent – run CLI subagents
  (claude/auggie/codex) on a task and compare their proposals. Runs only on request.
---

# /run.compare-subagent-outputs – Run CLI subagents on a task and compare their outputs

This command **generates** the proposals first (a paid fan-out over CLI subagents) and only then compares them. If the outputs already exist (a previous fan-out, a manual run, a colleague's analysis), use `/run-compare-agent-outputs` instead – it does the comparison only, spends no credits, and accepts a loose input format.

Thin entry point – **the entire procedure, CLI table, and Output Contract are in `.agents/agents/run.compare-subagent-outputs.md`** (do not duplicate them here). The command and the sub-agent have the same output; this command is the entry point for Claude Code and Auggie. (Codex does not support slash commands – invoke the `run.compare-subagent-outputs` sub-agent directly there.)

In short (details in the sub-agent):

1. Check CLI availability and **verify valid model-IDs** (`auggie model list`; `claude`/`codex` via `--help`).
2. Propose an agent × model matrix (**default `claude` and `auggie`**), warn about credit multiplication, and **wait for user confirmation**.
3. Prepare the prompt in a file with the **Output Contract** (exact text in the sub-agent) and run the orchestration script (`--check` before fan-out cheaply verifies auth/flags):
   ```bash
   .agents/agents/scripts/run.compare-subagent-outputs-fanout.sh \
     --prompt-file tmp/run.compare-subagent-outputs/prompt.md  claude auggie
   ```
4. Compare and analyze outputs; present a **recommended solution** (a proposal, not execution of changes) and provide the path to the `tmp/` folder containing the individual solutions.

Hard rules: only on request (never automatically), **no recursive execution** of the orchestrator, subagents only propose (they do not edit the repo), never include secrets in the prompt or argv (`.agents/rules/run.secret-safety.md`).

If the user provided an argument (task, which CLIs, how many, which models), narrow the procedure accordingly.
