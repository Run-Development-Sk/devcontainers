# AI agents

Devcontainer feature [`ai-agents`](https://github.com/RunDevelopmentSk/devcontainers).
Adds `claude`, `codex` and `auggie` CLI AI agents in the form of a [unified configuration](../docs/ai-agents.md).

## Installation

Copy the contents of the `features/ai-agents` folder into the project folder.

Add the following to the end of the `.devcontainer/post-create.sh` file:

```sh
# AI agents: install
bash "$(dirname "${BASH_SOURCE[0]}")/post-create-ai-agents.sh"
```

Add the following to the end of the `.devcontainer/post-start.sh` file:

```sh
# AI agents: materialize the symlinked rules dir that auggie can't read as a symlink
bash "$(dirname "${BASH_SOURCE[0]}")/post-start-ai-agents.sh"
```

Add the following to the `.gitignore` file:

```sh
#
# AI agents
#
# ignore local overrides (per-developer notes/settings, never commit)
*.local.md
*.local.json
*.local.toml
# ignore the materialized copy of .agents/rules (auggie symlinked-rules workaround),
# recreated on every container start by post-start-ai-agents.sh
.augment/rules
```

Remove this line from the `.gitignore` file if it exists:

```sh
/.antigravitycli/
```

If `CLAUDE.md` is a symlink to `AGENTS.md`, replace it with the `CLAUDE.md` file of this feature.
If it is already a file, keep its project-specific `## Claude Code specifics` section.

Add the following to the `.devcontainer/.env.init` file:

```sh
# define API key for run-transcribe skill
#TRANSCRIBE_OPENAI_API_KEY=???
```

Remove files if they exist:

- .agents/agents/run.compare-solutions.md
- .agents/agents/run.compare-solutions.toml
- .agents/agents/scripts/run.compare-solutions-fanout.sh
- .agents/commands/run.compare-solutions.md
- .agents/rules/run.dry-and-brief.md
- .devcontainer/agents.md
- .devcontainer/post-create-agents.sh, remove also mention in .devcontainer/post-create.sh
- .devcontainer/post-start-agents.sh, remove also mention in .devcontainer/post-start.sh
- GEMINI.md, .GEMINI.md, .agents/hooks.json (Antigravity configuration)
- tmp/.antigravity (symlink)
- the `odoo-developer-gemini` (or similarly named `.gemini`) volume mount and volume declaration in `.devcontainer/docker-compose.yml`
- commands that only wrapped a skill (the skill is invoked directly as `/run-<name>`):
  - .agents/commands/run.add-agent-asset.md
  - .agents/commands/run.compare-agent-outputs.md
  - .agents/commands/run.convert-to-markdown.md
  - .agents/commands/run.estimate-time.md
  - .agents/commands/run.integrate-devcontainer-addon.md
  - .agents/commands/run.remove-devcontainer-addon.md
  - .agents/commands/run.review-changes.md
  - .agents/commands/run.save-chat.md
  - .agents/commands/run.save-response.md
  - .agents/commands/run.transcribe.md

Rebuild the devcontainer.

## Known limitation

`post-start-ai-agents.sh` > `materialize_dir` is a **temporary workaround**: `auggie` currently fails to read any files through a symlinked directory (`.augment/rules` silently reports zero entries), so this script replaces that symlink with a real, gitignored directory containing a fresh copy of the source files on every container start. After editing `.agents/rules/`, reopen the devcontainer to get the changes copied over. See the [temporary workaround note](../docs/ai-agents.md#temporary-workaround-materialized-rules) in `docs/ai-agents.md` for details. Once the tool resolves symlinked directories correctly, drop `post-start-ai-agents.sh`, its call in `post-start.sh`, and go back to a plain symlink for `.augment/rules`.

## Removal

Delete everything that was added on installation, but ignore installation removals.

Rebuild the devcontainer.
