#!/bin/bash
# this script is used as "postCreateCommand" in devcontainer.json

# install python requirements
echo "" && echo "Installing python packages..."
# NOTE: Run it using `sudo` as `--break-system-packages` is not availble for pip in this image
sudo pip install -r ./.devcontainer/requirements.txt

# install CLI tools using pipx
echo "" && echo "Installing runtools..."
pipx install "runtools @ git+https://git@github.com/RunDevelopmentSk/runtools.git@main"

if command -v git >/dev/null 2>&1; then
    # git: add safe.directory exception for workspace folder (* = for any folder in fact)
    # because the project folder is bind-mounted from the host where it may be owned by
    # a different UID than the container user. This is mostly case on Windows.
    # Use append (>>) to avoid EBUSY caused by atomic rename on bind-mounted file.
    if ! grep -qE '^[[:space:]]*directory[[:space:]]*=[[:space:]]*\*[[:space:]]*$' "$HOME/.gitconfig" 2>/dev/null; then
        printf '\n[safe]\n\tdirectory = *\n' >> "$HOME/.gitconfig"
    fi

    # git: include the versioned project git config (core.hooksPath, merge drivers) into
    # .git/config, as git never applies a versioned config by itself (fajnwork projects
    # do the same in App::install())
    if [ -f default.gitconfig ] && git rev-parse --git-dir > /dev/null 2>&1; then
        if ! git config --local --get-all include.path | grep -qxF '../default.gitconfig'; then
            echo "" && echo "Including default.gitconfig into .git/config..."
            git config --local --add include.path ../default.gitconfig
        fi
    fi

    # git: install pre-commit hooks
    echo "" && echo "Installing precommit..."
    sudo pip install pre-commit
    hooks_path="$(git config --get core.hooksPath)"
    if [ -z "$hooks_path" ]; then
        pre-commit install
    else
        # pre-commit refuses to install its hook into .git/hooks which git ignores when
        # core.hooksPath is set, so the project provides its own pre-commit hook in that
        # folder (see .pre-commit-config.yaml) and here only hook environments are prefetched
        pre-commit install-hooks
        if [ ! -x "$hooks_path/pre-commit" ]; then
            echo "WARNING: core.hooksPath is set to '$hooks_path' but it contains no executable pre-commit hook - see .pre-commit-config.yaml > Installation."
        fi
    fi
fi
