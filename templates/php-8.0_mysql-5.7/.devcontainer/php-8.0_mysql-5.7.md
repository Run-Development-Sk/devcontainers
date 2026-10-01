# PHP 8.0 + MySQL 5.7

Devcontainer template [`php-8.0_mysql-5.7`](https://github.com/RunDevelopmentSk/devcontainers).
Development environment for PHP 8.0 projects with a MySQL 5.7 database, mostly
for projects built on the company PHP MVC framework "fajnwork".

## Installation

Copy the contents of the `templates/php-8.0_mysql-5.7` folder into the project
folder.

Find out whether the project is a fajnwork project: its `AGENTS.md` describes
the project as built on the "fajnwork" framework.

- **Fajnwork project**: keep `default.gitconfig`, `.gitattributes` and
  `.githooks/` as they are. Check that `App::install()` in
  `app/modules/Core/App.php` includes `default.gitconfig` into `.git/config`.
  If it still includes `default.hgrc` into `.hg/hgrc`, the project has not
  been migrated from Mercurial to Git yet.
- **Other project**: the files are fajnwork-specific in these places, so adapt
  or remove them:

  - `.gitattributes` (paths of compiled CSS files and `.po` files),
  - the React subprojects check and `gulp compile-less` in
    `.githooks/hooks.php`, together with the `post-checkout`, `post-merge` and
    `post-commit` wrappers if nothing remains in it.

  Keep `default.gitconfig` (`core.hooksPath`) and `.githooks/pre-commit`
  unless the project does not use `.pre-commit-config.yaml`.

Rebuild the devcontainer.

## Git configuration and hooks

- `default.gitconfig` is the versioned part of the git configuration:
  `core.hooksPath = .githooks` and the merge drivers used by `.gitattributes`.
  Git never applies a versioned configuration by itself, and nothing can run
  automatically on `git clone`. That is why it is included into `.git/config`
  by:
  - `.devcontainer/post-create.sh` when the devcontainer is created, for every
    project with `default.gitconfig`,
  - `App::install()` on the first request in fajnwork projects. This covers
    installations outside the devcontainer (staging, production). Bumping
    `App::$installModificationDatetime` makes existing installations run it
    again.
  - In any other case (a non-fajnwork project outside the devcontainer, or a
    repository cloned or initialized after the devcontainer was created), run
    manually: `git config --local --add include.path ../default.gitconfig`
- Verify the setup with `git config --show-origin core.hooksPath`. It must
  print `.githooks`, coming from `.git/../default.gitconfig`.
- `.gitattributes` keeps the local version of compiled CSS and map files on
  merge (`keep-local`) and merges `.po` files by `msgcat` (`pomerge`).
- `.githooks/` holds the hooks. Their behaviour is described in
  `.githooks/hooks.php`.
  - `post-checkout`, `post-merge` and `post-commit` call
    `.githooks/hooks.php`. Rebase and `git pull --rebase` are covered by
    `post-checkout`.
  - `pre-commit` runs the hooks from `.pre-commit-config.yaml`. Do not run
    `pre-commit install`: it refuses to work when `core.hooksPath` is set.
    `post-create.sh` only prefetches the hook environments.
- Requirements, all provided by the docker image:
  - `php`,
  - `msgcat` (gettext),
  - node 17 with a global `gulp`, installed through nvm. The hooks launch
    `gulp` by `nvm exec --silent 17`, so the node version of the shell stays
    untouched.
- The hook wrappers are copies, not symlinks, so they also work on Windows.
  Keep their executable bit in git (`git update-index --chmod=+x <file>`).
  Otherwise git skips them silently.
- Checking out a commit older than `.githooks/` runs no hooks.

## Removal

Delete everything that was added on installation. Then remove the include from
`.git/config`:
`git config --local --unset include.path '^\.\./default\.gitconfig$'`

Rebuild the devcontainer.
