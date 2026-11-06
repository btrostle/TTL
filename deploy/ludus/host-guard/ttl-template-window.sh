#!/usr/bin/env bash
# Open the TTL range guard for Packer template builds, then close it again.
#
# Run as root on the Ludus host:
#   ttl-template-window.sh [template-name ...]
#
# With names, starts `ludus templates build -n <name>` for each one. Without,
# start the builds yourself (CLI or web UI). Either way, press Enter once
# `ludus templates status` shows nothing building. The guard is reloaded on
# exit, including on errors and Ctrl-C, which removes the allow rule.
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Run as root on the Ludus host." >&2; exit 1; }
nft list table inet ttl_range_guard >/dev/null 2>&1 ||
    { echo "ttl_range_guard is not loaded; nothing to open." >&2; exit 1; }

close() {
    systemctl reload ttl-range-guard
    if nft list chain inet ttl_range_guard input | grep -q ttl-template-window; then
        echo "WARNING: template allow is still loaded. Run: systemctl reload ttl-range-guard" >&2
        exit 1
    fi
    echo "Guard closed: template allow removed."
}
trap close EXIT

nft insert rule inet ttl_range_guard input iifname vmbr1000 \
    ip saddr 192.0.2.50-192.0.2.100 accept comment '"ttl-template-window"'
echo "Guard open: 192.0.2.50-100 may reach this host."

for name in "$@"; do
    ludus templates build -n "$name"
done

echo "Watch progress with: ludus templates status"
read -rp "Press Enter when every build has finished (or failed)... " _
