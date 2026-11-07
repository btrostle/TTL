# Ludus host guard

Layer 2 of home-network isolation (see `docs/ranges.md`). Layer 1 is
`network.always_blocked_networks` in each range config, enforced on the
range router. Agents have root on range routers and can upload range
configs, so layer 1 can be undone from inside the lab. This guard runs on
the Ludus host, which agents never reach. The owner installs and maintains
it.

## What it does

Range routers' WAN interfaces sit on the Ludus NAT bridge `vmbr1000`
(192.0.2.0/24; range N's router is `192.0.2.(100+N)`, template builds use
`.50-.100`, the host is `.254`). Every packet a range sends outside itself
arrives on that bridge. For traffic arriving on `vmbr1000`, the guard:

| Traffic | Result |
|---|---|
| Internet, routed out the host's uplink | allowed |
| Replies to connections the host or WireGuard clients open into ranges | allowed |
| DHCP, DNS and ping to the host | allowed |
| Private and reserved networks (home, other ranges, CGNAT, ...) | dropped |
| Anything else to the host (Proxmox 8006, Ludus API 8080, SSH, ...) | dropped |
| New connections to Ludus WireGuard clients (198.51.100.0/24) | dropped |
| IPv6 forwarding | dropped |

Range routers can also reach each other directly over `vmbr1000`. That
traffic is bridged, not routed, so the table above never sees it. A second
table, `bridge ttl_range_bridge`, filters frames between VMs on the bridge:

| Traffic between VMs on `vmbr1000` | Result |
|---|---|
| Any range router to the TTL-SIEM router (`$siem_wan`), TCP 8220 and 9200, and the replies | allowed |
| ARP | allowed |
| Anything else (router to router, template VMs to routers) | dropped |

Traffic inside a range (between its VMs and VLANs) never reaches the host,
so the guard does not affect it. Drops are logged, rate-limited, with the
prefix `ttl-range-guard drop:`.

The rules live in their own tables (`inet ttl_range_guard` and
`bridge ttl_range_bridge`), so they leave
Ludus's iptables rules and any Proxmox firewall alone. Debian's
`nftables.service` is not used, because its default config runs
`flush ruleset`, which would also wipe other tables. Bridge drops are
logged with the prefix `ttl-range-guard bridge drop:`.

## Files

- `ttl-range-guard.nft`: the ruleset. Loading it replaces only its table.
- `local.nft.example`: host-specific settings, installed as
  `/etc/ttl-range-guard.local.nft` (not tracked).
- `ttl-range-guard.service`: loads the ruleset at boot, before the network.
- `ttl-template-window.sh`: opens the guard for Packer template builds.

## Install

On the Ludus host, as root, from this directory:

```sh
command -v nft || apt install nftables     # do not enable nftables.service
iptables-save -t nat | grep MASQUERADE     # the -o interface is the uplink
install -m 0644 local.nft.example /etc/ttl-range-guard.local.nft
$EDITOR /etc/ttl-range-guard.local.nft     # set uplink and siem_wan
install -m 0644 ttl-range-guard.nft /etc/ttl-range-guard.nft
nft -c -f /etc/ttl-range-guard.nft         # syntax check, loads nothing
install -m 0644 ttl-range-guard.service /etc/systemd/system/
install -m 0755 ttl-template-window.sh /usr/local/sbin/
systemctl daemon-reload
systemctl enable --now ttl-range-guard
nft list table inet ttl_range_guard
nft list table bridge ttl_range_bridge
```

To update: install the new `ttl-range-guard.nft`, check it with `nft -c`,
then `systemctl reload ttl-range-guard`.

Rollback: `systemctl disable --now ttl-range-guard` (deletes both tables).

When TTL-SIEM is created or renumbered, set `siem_wan` in
`/etc/ttl-range-guard.local.nft` to `192.0.2.(100 + its range number)`
and reload. Until then the placeholder `192.0.2.100` matches no router.

## Verify

From a running range router (login from `GET /range/ansibleinventory`,
password auth). Routers have no `nc`, so use bash:

```bash
for t in 192.0.2.254:8006 192.0.2.254:8080 192.0.2.254:22 <host-ip>:8006 <home-ip>:53 1.1.1.1:443; do
  h=${t%:*}; p=${t#*:}
  if timeout 3 bash -c "</dev/tcp/$h/$p" 2>/dev/null; then echo "OPEN    $t"; else echo "blocked $t"; fi
done
```

Everything should be blocked except `1.1.1.1:443`.

To check the bridge table, run this from one range router while another
range is up (`<other>` is that range's router, `192.0.2.(100+N)`):

```bash
for t in <other>:22 <siem>:22 <siem>:5601 <siem>:8220 <siem>:9200; do
  h=${t%:*}; p=${t#*:}
  if timeout 3 bash -c "</dev/tcp/$h/$p" 2>/dev/null; then echo "OPEN    $t"; else echo "blocked $t"; fi
done
```

Only `<siem>:8220` and `<siem>:9200` should be open. The router starts these
connections itself, so its own forwarding rules (layer 1) don't apply, and
the check tests the guard alone.

On the host, `nft list table inet ttl_range_guard` shows counters and
`journalctl -k | grep ttl-range-guard` shows drops.

## Template builds

Some Packer templates serve their install answer file from a temporary HTTP
server on the host. The template VM (192.0.2.50-100) fetches it from
`192.0.2.254`, which the guard blocks, so the install hangs. Find these
templates with:

```sh
grep -rlE 'HTTPIP|http_directory|http_content' /opt/ludus/templates /opt/ludus/users/*/packer
```

Build them through the window script, which allows the template pool,
starts the builds, waits for Enter, and reloads the guard on any exit
(including errors and Ctrl-C):

```sh
ttl-template-window.sh <template-name> [...]
```

Don't leave the pool allowed: a range router with root can take a pool
address and would then reach every service on the host.
