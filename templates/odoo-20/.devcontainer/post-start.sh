#!/bin/bash
# this script is used as "postStartCommand" in devcontainer.json

# create symbolic link to odoo sources to have it accessible inside project folder
rm -rf /mnt/odoo-sources
ln -s /usr/lib/python3/dist-packages/odoo /mnt/odoo-sources

# create symbolic link to odoo log to have it accessible inside project folder
rm -rf /mnt/tmp/log
ln -s /var/log/odoo /mnt/tmp/log

# clear log file
truncate -s 0 /var/log/odoo/odoo.log 2>/dev/null || true

# create scratchpad file if it does not exist
echo "" && echo "Creating scratchpad file..."
SCRATCHPAD_DIR="$(dirname "${BASH_SOURCE[0]}")/../tmp"
SCRATCHPAD_FILE="${SCRATCHPAD_DIR}/tmp.txt"
if [ ! -f "${SCRATCHPAD_FILE}" ]; then
    mkdir -p "${SCRATCHPAD_DIR}"
    echo "This is your scratchpad..." > "${SCRATCHPAD_FILE}"
fi
