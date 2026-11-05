---
name: run-odoo-restart-reminder
description: Reminder on how (and when) to restart or update Odoo after code changes. Always use when you have made changes to modules, manifests, models, views, or data files. NEVER start or update Odoo automatically – only notify the user.
---

# run-odoo-restart-reminder

After changing source files, it is necessary for the user to manually restart/update Odoo.
**The agent must not do this automatically** (so the user has control over the restart and logs, and to avoid interrupting ongoing work).

## When to warn and what to suggest

| Type of Change                                                              | Recommended Command                | Note                                                 |
| --------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------- |
| Python code (`*.py`)                                                        | `make odoo` or `odoo --dev reload` | `--dev reload` captures changes without restarting   |
| Manifest (`__manifest__.py`), models with new fields, security, data, views | `odoo -u <module>`                 | Triggers module upgrade (DB migration + view reload) |
| Multiple modules                                                            | `odoo -u module_a,module_b`        | Comma-separated list                                 |
| Specific DB                                                                 | `odoo -d <db> -u <module>`         | The default DB is `odoo`                             |
| New module (first installation)                                             | Apps → Update Apps List → Install  | Via UI; or `odoo -i <module>`                        |

## Wording of the warning

Standard sentence at the end of the task:

> The changes require restarting/upgrading Odoo. Please run **manually**:
> `odoo -u <modules>` (and optionally `-d <db>` if you are not using the default `odoo`).

## Anti-pattern

- ❌ Do not run `odoo …` via any shell/process-launching tool of the agent, nor in any script within an automated task.
- ❌ Do not restart the systemd service `odoo.service`.
- ❌ Do not use `pkill odoo` or `kill -HUP`.
