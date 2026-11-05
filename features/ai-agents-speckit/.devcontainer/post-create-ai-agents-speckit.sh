#!/bin/bash

# spec-kit (https://github.com/github/spec-kit) - Spec-Driven Development toolkit.
#
# Unlike Superpowers, only the official installation method is used here (no vendoring):
# the `specify` CLI is installed via `uv tool install` (officially recommended method,
# see docs/installation.md), then the project is initialized (`specify init --here`) and
# an integration (see docs/reference/integrations.md) is installed for each of the 3 AI
# agents present in this devcontainer (see docs/ai-agents.md): auggie, claude, codex.
#
# Version to install: "latest" (default) always fetches the newest release tag; set to a
# concrete tag (e.g. "v0.12.5") to pin a specific version instead.
#
# This variable may be preset/exported by the caller before running this script; the value
# below is only the default used when not already set.
SPECKIT_VERSION="${SPECKIT_VERSION:-latest}"

if [ "$SPECKIT_VERSION" = "latest" ]; then
  SPECKIT_VERSION=$(curl -fsSL -o /dev/null -w '%{url_effective}' \
    "https://github.com/github/spec-kit/releases/latest" | sed 's#.*/tag/##')
fi

echo "" && echo "Installing spec-kit CLI (specify-cli ${SPECKIT_VERSION})..."
uv tool install specify-cli --from "git+https://github.com/github/spec-kit.git@${SPECKIT_VERSION}"
echo "spec-kit CLI (specify): $(specify version || true)"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root" || exit 1

# Initialize the project (creates .specify/ with templates, scripts, memory) with the first
# integration (auggie). Skipped if already initialized (e.g. on container rebuild).
if [ ! -d "$repo_root/.specify" ]; then
  echo "" && echo "Initializing spec-kit project (.specify/) with 'auggie' integration..."
  specify init --here --force --script sh --ignore-agent-tools --integration auggie
else
  echo "" && echo "Skipping 'specify init' (.specify/ already exists)"
fi

# Install the remaining integrations. `claude` and `codex` are declared "multi-install safe"
# alongside `auggie` (see docs/reference/integrations.md), so no --force is needed. Errors
# (e.g. integration already installed) are tolerated so the script stays idempotent across
# container rebuilds.

# The `claude` integration writes Claude-specific skill files (extra frontmatter fields:
# argument-hint, user-invocable, disable-model-invocation) that differ from the generic
# format written by `auggie`/`codex`. The unified AI-agent configuration (see
# docs/ai-agents.md) normally makes `.claude/skills` a symlink to `.agents/skills`, so
# installing `claude` alongside the other integrations would make them overwrite each
# other's skill files in the same physical location. To avoid this, set aside the symlink
# (renamed to `.claude/skills-shared`, left untouched so the unified config can be
# restored later) and replace `.claude/skills` with a real, independent directory (seeded
# with a copy of the current .agents/skills content) before installing the `claude`
# integration.
if [ -L "$repo_root/.claude/skills" ]; then
  echo ""
  echo "WARNING: setting aside the unified '.claude/skills -> ../.agents/skills' symlink as"
  echo "         '.claude/skills-shared' so '.claude/skills' can become a REAL, independent"
  echo "         directory (seeded with a copy of '.agents/skills') holding spec-kit's"
  echo "         Claude-specific skill files without colliding with the other agents. It is"
  echo "         NO LONGER covered by the unified AI-agent skills configuration described in"
  echo "         docs/ai-agents.md."
  cp -rL "$repo_root/.agents/skills" "$repo_root/.claude/skills.tmp"
  mv "$repo_root/.claude/skills" "$repo_root/.claude/skills-shared"
  mv "$repo_root/.claude/skills.tmp" "$repo_root/.claude/skills"
fi

echo "" && echo "Installing spec-kit integration for 'claude'..."
specify integration install claude --script sh \
  || echo "Skipping spec-kit integration 'claude' (already installed or failed)"

echo "" && echo "Installing spec-kit integration for 'codex'..."
specify integration install codex --script sh \
  || echo "Skipping spec-kit integration 'codex' (already installed or failed)"
