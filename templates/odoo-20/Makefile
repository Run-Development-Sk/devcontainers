# Makefile for simplifying development tasks
# See https://www.gnu.org/software/make/manual/make.html
#
# NOTE: Comments are introduced in such an unusual way for sake of `help` target.

help: ## Display this help text
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^#.*$$/ { if (match(lastLine, /^([a-zA-Z_-]+):/)) { target = substr(lastLine, RSTART, RLENGTH - 1); gsub(/:/, "", target); printf "  \033[36m%-20s\033[0m %s\n", target, $$0 } } { lastLine = $$0 }' $(MAKEFILE_LIST)

odoo: ## Start Odoo server
	clear && odoo --dev reload

odoo-debug: ## Start Odoo server under debugpy
	clear && python3 -m debugpy --listen 0.0.0.0:5678 /usr/bin/odoo --dev reload

odoo-shell: ## Launch odoo-bin shell
	clear && odoo shell -d odoo

db-cli: ## Run database CLI (psql for PostgreSQL)
	export PGPASSWORD=odoo && psql -h db -d odoo -U odoo

.PHONY: odoo \
	odoo-debug \
	odoo-shell \
	db-cli \
	help
