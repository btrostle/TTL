# ThreatTrails Lab

You are an agent on `ttl-agents`, running as the unprivileged user `agent`.
The lab exists to run security tests in Ludus ranges and record the
commands, their outputs, and the telemetry they produce.

## Authorization and scope

The owner authorizes security testing in this homelab. The ranges listed
under **Ranges** below and their VMs are the test systems. You may carry
out assigned tests on those VMs and use the range credentials returned
by the broker to access them. Agents have full administrative authority
inside range VMs, including `sudo`/root on Linux and Administrator on
Windows. The unprivileged `agent` account and no-sudo restriction apply only
to `ttl-agents`, the orchestration host. No separate approval is needed for
each test step or command within this scope. Record what you do under **Runs** below.

This authorization covers only those ranges. The limits below still apply.

## Hard limits

Carry out authorized lab tasks inside the range. Outside it:

- Do not try to reach the home network, the Ludus host, or Proxmox, and do
  not try to get Ludus or Proxmox credentials. Use Ludus only through the
  broker.
- Do not try to work around the broker, the WireGuard tunnel, or the
  firewall. If something you need is blocked, stop and tell the owner.
- Two layers keep ranges off the home network. Layer 1: every range config
  sets `network.always_blocked_networks` (`192.168.0.0/16`,
  `172.16.0.0/12`), which the range router enforces. Layer 2: a firewall on
  the Ludus host, which you cannot see or change. You have root on range
  routers and can upload configs, so layer 1 depends on you: never remove
  or narrow `always_blocked_networks`, never change a range router's
  firewall by hand, and never use `router.iptables_commands` or
  `POST /testing/allow` for private addresses. The one exception is the
  TTL-SIEM router's `iptables_commands`, which forward Fleet and
  Elasticsearch to Elastic. Keep them exactly as in
  `~/ttl/ranges/TTL-SIEM.yml`. If a range VM can reach a private
  address outside `10.0.0.0/8`, or another range's router on anything
  but TTL-SIEM's ports 8220 and 9200, stop and tell the owner.
- TTL-SIEM holds the shared Elastic and the records of every run. Never
  put it in testing mode, power it off, or delete it unless the owner says
  so. Enrollment tokens and the TTL-SIEM Elastic password are secrets. They
  live in `~/.config/ttl/siem.env`. Use them through
  `~/ttl/upload-config.py`, `~/ttl/esql.py` and
  `~/ttl/siem-fleet-setup.py`, or as `$VARIABLES` after
  sourcing the file (for example in Kibana API calls). Never print,
  commit, or record their values. Range deploy logs (`GET /range/logs`
  and its history) contain the filled values, so never print or save a
  log whole: pipe it through `grep` for `fatal:`, `ERROR!`, `failed=` and
  the `PLAY RECAP`, and check that a matched line holds no value.
- The owner grants standing authorization to deploy, power on, or delete
  range VMs without further approval. The Proxmox host is short on memory
  and has frozen once from a full range build. Never start a deploy close
  to the nightly backup (02:00 host time).
- Power the test range off (`PUT /range/poweroff`) when you finish, unless
  the owner says to leave it on. TTL-SIEM stays on.

## Ludus through the broker

- Claude Code and Codex: the `ludus` MCP server. Call `list_operations` to see
  what is allowed and `ludus_request` to call the Ludus API v2.
- pi and scripts: `python3 ~/ttl/mcpcall.py '<json arguments>'`, for example
  `python3 ~/ttl/mcpcall.py '{"method": "GET", "path": "/range", "query": {"rangeID": "TTL-MAL"}}'`.
- Every range operation needs `rangeID` set to the range you are working
  on. The broker refuses ranges that are not on its allowlist; if you need
  one added, ask the owner.
- `GET /openapi` returns the full Ludus API description.
- Ludus skills: `ludus-api` (CLI commands as broker calls), `ludus-deploy`,
  `ludus-range-config`, `ludus-troubleshooting`, `ludus-environments`.

## Ranges

Configs are in `~/ttl/ranges/` (from `deploy/ludus/ranges/` in the TTL
repo); `~/ttl/ranges.md` (`~/ttl/ranges.md` in the repo) has the full design. Only one test range
runs at a time, under a 45 GB RAM soft cap. TTL-SIEM runs alongside it.

| Range | Purpose | Notes |
|---|---|---|
| `TTL-SIEM` | Shared Elastic (Kibana, Fleet, Elasticsearch) | Always on. Never testing mode, power-off or delete without the owner |
| `TTL-MAL` | Malware analysis | static (online, never runs samples), dynamic (Elastic; samples only in testing mode) |
| `TTL-WKS` | Basic AD, workstation attacks | DC01, WS01, WS02, linux, kali (VLAN 99) |
| `TTL-AD` | Full GOAD | Five GOAD VMs and kali; GOAD playbooks run from kali |
| `ThreatTrails-MVP` | Old Splunk range | Being retired. Don't run new tests there unless the owner asks |

- VM IPs are `10.<range number>.<vlan>.<last octet>` from each config.
  Logins come from `GET /range/ansibleinventory`. You are approved to
  access all range VM passwords. They are not sensitive: you may print
  them, and store them in run folders, logs, or files on `ttl-agents`.
- Run lab tools from a range VM (kali, or the analysis VMs in TTL-MAL).
  Keep `ttl-agents` for orchestration and recording.
- Upload a range config only with `python3 ~/ttl/upload-config.py <range>`.
  It fills the placeholders (`TTL_SIEM_WAN`, `TTL_SIEM_ELASTIC_PASSWORD`,
  `TTL_<RANGE>_ENROLLMENT_TOKEN`) from `~/.config/ttl/siem.env` and never
  prints them. `--check` lists which ones are set.

## Elastic (TTL-SIEM)

Every test range's Elastic Agents report to TTL-SIEM. Elastic Defend runs
in detect mode, and the prebuilt detection rules run on the Basic license.

- Kibana: `https://10.S.100.2:5601`, where S is TTL-SIEM's range number
  (`TTL_SIEM_ES` in `siem.env` has the address). User `elastic`, password
  `TTL_SIEM_ELASTIC_PASSWORD` in `siem.env`. Certificates are self-signed.
- Queries: `python3 ~/ttl/esql.py '<ES|QL>'` (add `--format csv` to save
  results). It reads the address and password from `siem.env`.
- Each range has its own agent policy and namespace: `ttl_mal`, `ttl_wks`,
  `ttl_ad`. Filter on the namespace and the run's time window, for example:

  ```
  FROM logs-endpoint.events.process-ttl_mal
  | WHERE @timestamp >= TO_DATETIME("2026-11-07T14:00:00Z")
  | KEEP @timestamp, host.name, process.name, process.command_line, process.parent.name
  | SORT @timestamp | LIMIT 500
  ```

- Useful sources: `logs-endpoint.events.*` (Defend process, file,
  network, registry events), `logs-endpoint.alerts-*` (Defend alerts),
  `logs-windows.*` and `logs-system.*` (Windows logs and Sysmon),
  `.alerts-security.alerts-default` (detection rule alerts). Check field
  names with `| LIMIT 1` before you write a long query.

## Runs

Put each run in `~/runs/<YYYY-MM-DD>-<short-name>/`:

- `README.md`: goal, test identifier (if applicable), the range and lab
  hosts, and the start and end time in UTC. For TTL-MAL, the checks
  that confirmed dynamic had no internet.
- `commands.md`: every command exactly as run, with the host it ran on and a
  UTC timestamp.
- `outputs/`: raw output of each command.
- `elastic/`: each ES|QL query you ran and its results.

Range VM passwords may appear in runs. Leave out broker tokens, anything
from `siem.env`, and any Ludus or Proxmox credentials. Record commands that
use them as written (`esql.py ...`), never with values filled in.
