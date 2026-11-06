#!/bin/sh
# Lock down an agents box. Run as root on a fresh Ubuntu 24.04 VM, with the
# Ludus WireGuard config for the agents' own Ludus user at /root/ludus-wg.conf:
#   sudo sh agents-box.sh
#
# Afterwards: agents run as the unprivileged user "agent", reach the range
# subnets over a root-owned tunnel, and cannot reach the Ludus host
# (198.51.100.1), read the tunnel key, change routes, or sudo.
set -eu

ludus_host=198.51.100.1

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wireguard-tools nftables >/dev/null

# Tunnel: root-only config, without the route to the Ludus host.
if [ -f /root/ludus-wg.conf ]; then
    install -d -m 700 /etc/wireguard
    sed -E "/^AllowedIPs/ s#(^|[ ,=])$ludus_host/32,?#\1#; /^AllowedIPs/ s#,\s*\$##" \
        /root/ludus-wg.conf > /etc/wireguard/ludus.conf
    chmod 600 /etc/wireguard/ludus.conf
    rm /root/ludus-wg.conf
fi
grep -q "$ludus_host" /etc/wireguard/ludus.conf && { echo "Ludus host still routed" >&2; exit 1; }
systemctl enable --now wg-quick@ludus >/dev/null

# Agent user: no sudo, no admin groups.
id agent >/dev/null 2>&1 || useradd --create-home --shell /bin/bash agent
chmod 750 /home/agent
for g in sudo adm lxd docker libvirt disk; do gpasswd -d agent "$g" >/dev/null 2>&1 || true; done
install -d -m 700 -o agent -g agent /home/agent/.ssh

# Backstop if the tunnel config ever routes the Ludus host again.
cat > /etc/nftables.conf <<EOF
#!/usr/sbin/nft -f
flush ruleset
table inet ttl_agents {
    chain output {
        type filter hook output priority 0; policy accept;
        meta skuid "agent" ip daddr $ludus_host counter reject
    }
}
EOF
systemctl enable nftables >/dev/null
systemctl restart nftables
