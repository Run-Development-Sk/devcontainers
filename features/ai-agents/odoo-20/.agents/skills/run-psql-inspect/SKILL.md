---
name: run-psql-inspect
description: Inspect the structure and content of the Odoo PostgreSQL database via `psql` in the devcontainer. Use when you need to verify the existence of a table or columns, or to load actual data from a live database.
---

# run-psql-inspect

The devcontainer has PostgreSQL access on host `db`, user `odoo`, password `odoo`,
database `odoo`. Shortcut via `Makefile`: `make db-cli` (opens interactive `psql`).

These credentials are well-known defaults of the local devcontainer environment only
(they are not production credentials and are not secrets in the sense of
`.agents/rules/run.secret-safety.md`), so using them literally in commands here is fine.

## Common Queries

```bash
# List all tables
PGPASSWORD=odoo psql -h db -U odoo -d odoo -c "\dt"

# Structure of a specific table
PGPASSWORD=odoo psql -h db -U odoo -d odoo -c "\d res_users"

# Table content
PGPASSWORD=odoo psql -h db -U odoo -d odoo -c "SELECT id, login FROM res_users LIMIT 20"

# Find tables matching a pattern (e.g., `stock` module)
PGPASSWORD=odoo psql -h db -U odoo -d odoo -c "\dt stock_*"

# Filtered list of table columns
PGPASSWORD=odoo psql -h db -U odoo -d odoo \
  -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='res_partner'"
```

## Conventions

- **Never** write `UPDATE`/`DELETE`/`INSERT` statements directly via `psql`. Modify data through the Odoo ORM
  (module, demo data, `odoo shell`), not through raw SQL – to maintain the consistency of
  computed fields, ACL rules, and the audit log.
- If you need a schema migration, use the Odoo migration framework in `<module>/migrations/<version>/`,
  not manual `ALTER TABLE` statements.
- Do not print sensitive data (passwords, tokens) to the logs or chat output.

## Related

- Odoo shell: `make odoo-shell` (Python REPL with `env`)
- Makefile target: `make db-cli`
