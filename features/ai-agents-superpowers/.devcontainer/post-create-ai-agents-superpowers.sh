#!/bin/bash

# Superpowers (https://github.com/obra/superpowers) skills library.
#
# SUPERPOWERS_INSTALL controls how it gets installed:
#   - "original" (default) installs the official plugin separately for claude and codex via
#                 their own CLI plugin managers (global, per-user cache, NOT versioned in
#                 this repo, NOT shared with auggie - auggie has no plugin manager, so it
#                 would not get Superpowers at all with this option).
#   - "vendor"    downloads the skills/ directory and copies it into the
#                 unified .agents/skills/ (see docs/ai-agents.md), so all 3 agents
#                 (auggie, claude, codex) share one versioned, repo-committed copy.
#                 Also registers a SessionStart hook (see register_session_start_hook())
#                 for claude, codex and auggie that simulates Superpowers' own bootstrap
#                 injection (see .agents/hooks/superpowers-session-start.sh).
#
# This variable may be preset/exported by the caller (e.g. post-create-ai-agents.sh) before
# running this script; the value below is only default used when not already set.
SUPERPOWERS_INSTALL="${SUPERPOWERS_INSTALL:-original}"

# Version to download for "vendor": "latest" (default) always fetches the newest release
# tag; set to a concrete tag (e.g. "v6.1.1") to pin a specific version instead.
# (Ignored for "original" - each agent's plugin manager tracks its own version.)
#
# This variable may be preset/exported by the caller (e.g. post-create-ai-agents.sh) before
# running this script; the value below is only default used when not already set.
SUPERPOWERS_VERSION="${SUPERPOWERS_VERSION:-latest}"

install_vendor() {
  local skills_dest_dir
  skills_dest_dir="$(dirname "${BASH_SOURCE[0]}")/../.agents/skills"

  if [ "$SUPERPOWERS_VERSION" = "latest" ]; then
    SUPERPOWERS_VERSION=$(curl -fsSL -o /dev/null -w '%{url_effective}' \
      "https://github.com/obra/superpowers/releases/latest" | sed 's#.*/tag/##')
  fi
  local tarball_url="https://github.com/obra/superpowers/archive/refs/tags/${SUPERPOWERS_VERSION}.tar.gz"

  echo "" && echo "Downloading Superpowers skills (${SUPERPOWERS_VERSION})..."

  local tmp_dir
  tmp_dir=$(mktemp -d)
  trap 'rm -rf "$tmp_dir"' RETURN

  curl -fsSL "$tarball_url" -o "$tmp_dir/superpowers.tar.gz"
  tar -xzf "$tmp_dir/superpowers.tar.gz" -C "$tmp_dir"

  local src_dir
  src_dir=$(find "$tmp_dir" -maxdepth 1 -type d -name "superpowers-*")

  mkdir -p "$skills_dest_dir"

  # copy each skill, without overwriting any existing project-specific skill of the same name
  for skill_dir in "$src_dir"/skills/*/; do
    local skill_name dest
    skill_name=$(basename "$skill_dir")
    dest="$skills_dest_dir/$skill_name"
    if [ -e "$dest" ]; then
      echo "Skipping Superpowers skill '$skill_name' (already exists in $skills_dest_dir)"
    else
      cp -r "$skill_dir" "$dest"
      echo "Installed Superpowers skill: $skill_name"
    fi
  done

  echo "Superpowers skills (${SUPERPOWERS_VERSION}) installed to $skills_dest_dir"

  register_session_start_hook
}

# Simulates the official Superpowers SessionStart hook (which the vendored skill copy does not
# come with) by registering .agents/hooks/superpowers-session-start.sh as a SessionStart hook in
# the project settings of claude, codex and auggie (identical JSON schema, see docs/ai-agents.md
# > "Hooks"). All 3 run project-level hooks with the repository root as cwd, so a plain relative
# path works for all of them (matches the assumption already made inside the hook script itself).
# Non-destructive: merges into each settings file's existing "hooks.SessionStart" array instead
# of overwriting the file, and skips a target if the same hook command is already present.
register_session_start_hook() {
  local repo_root hook_command
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  hook_command='bash .agents/hooks/superpowers-session-start.sh'

  echo "" && echo "Registering Superpowers SessionStart hook for claude, codex and auggie..."

  register_session_start_hook_json "$repo_root/.claude/settings.json" "$hook_command"
  register_session_start_hook_json "$repo_root/.codex/hooks.json" "$hook_command"
  register_session_start_hook_json "$repo_root/.augment/settings.json" "$hook_command"
}

# Merges a SessionStart command hook entry into a settings JSON file (creating the file/parent
# directory if needed), without touching any other existing content. Skips silently if a
# SessionStart hook with the exact same command is already registered.
#   $1 - path to the settings JSON file (e.g. .claude/settings.json)
#   $2 - shell command to run
register_session_start_hook_json() {
  local settings_file="$1" command="$2"
  mkdir -p "$(dirname "$settings_file")"
  python3 - "$settings_file" "$command" << 'PYEOF'
import json
import sys

settings_file, command = sys.argv[1], sys.argv[2]

try:
    with open(settings_file) as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

hooks = settings.setdefault("hooks", {})
session_start = hooks.setdefault("SessionStart", [])

for entry in session_start:
    for hook in entry.get("hooks", []):
        if hook.get("command") == command:
            print(f"Skipping SessionStart hook for {settings_file} (already registered)")
            sys.exit(0)

session_start.append({"hooks": [{"type": "command", "command": command}]})

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

print(f"Registered SessionStart hook in {settings_file}")
PYEOF
}

install_per_agent() {
  # Claude Code CLI
  if command -v claude >/dev/null 2>&1; then
    echo "" && echo "Installing Superpowers plugin for Claude Code..."
    claude plugin marketplace add obra/superpowers-marketplace
    claude plugin install superpowers@superpowers-marketplace --scope project
  else
    echo "Skipping Superpowers plugin for Claude Code (claude CLI not found)"
  fi

  # Codex CLI
  # NOTE: "superpowers-dev" is the marketplace name Codex derives from the
  # obra/superpowers repo itself (it is not configurable via the add command).
  if command -v codex >/dev/null 2>&1; then
    echo "" && echo "Installing Superpowers plugin for Codex..."
    codex plugin marketplace add obra/superpowers
    codex plugin add superpowers@superpowers-dev
  else
    echo "Skipping Superpowers plugin for Codex (codex CLI not found)"
  fi

  # Auggie has no plugin/marketplace mechanism - it needs the vendored .agents/skills/
  # copy to get Superpowers at all (run this script with SUPERPOWERS_INSTALL="vendor").
  echo "" && echo "NOTE: Auggie has no plugin manager - it will NOT have Superpowers unless also vendored into .agents/skills/."
}

case "$SUPERPOWERS_INSTALL" in
  vendor)
    install_vendor
    ;;
  original)
    install_per_agent
    ;;
  *)
    echo "Unknown SUPERPOWERS_INSTALL value: '$SUPERPOWERS_INSTALL' (expected 'vendor' or 'original')" >&2
    exit 1
    ;;
esac
