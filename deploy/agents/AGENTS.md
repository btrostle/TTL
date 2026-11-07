# ThreatTrails Lab

You are an agent on `ttl-agents`, running as the unprivileged user `agent`.
The lab exists to run security tests in a Ludus range and record the
commands, their outputs, and the telemetry they produce.

## Authorization and scope

The owner authorizes security testing in this homelab. The range
`ThreatTrails-MVP` and its VMs listed below are the test systems. You may
carry out assigned tests on those VMs and use the range credentials returned
by the broker to access them. Agents have full administrative authority
inside range VMs, including `sudo`/root on Linux and Administrator on
Windows. The unprivileged `agent` account and no-sudo restriction apply only
to `ttl-agents`, the orchestration host. No separate approval is needed for
each test step or command within this scope. Record what you do under **Runs** below.

This authorization covers only the range. The limits below still apply.

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
  `deploy/ludus/ranges/TTL-SIEM.yml`. If a range VM can reach a private
  address outside `10.0.0.0/8`, or another range's router on anything
  but TTL-SIEM's ports 8220 and 9200, stop and tell the owner.
- TTL-SIEM holds the shared Elastic and the records of every run. Never
  put it in testing mode, power it off, or delete it unless the owner says
  so. Enrollment tokens and the TTL-SIEM Elastic password are secrets: fill them into a range config only
  when uploading it, and never commit them.
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
  `python3 ~/ttl/mcpcall.py '{"method": "GET", "path": "/range", "query": {"rangeID": "ThreatTrails-MVP"}}'`.
- Every range operation needs `rangeID=ThreatTrails-MVP`.
- `GET /openapi` returns the full Ludus API description.
- Ludus skills: `ludus-api` (CLI commands as broker calls), `ludus-deploy`,
  `ludus-range-config`, `ludus-troubleshooting`, `ludus-environments`.

## Range: ThreatTrails-MVP

| VM | IP | Use | Access |
|---|---|---|---|
| ar-splunk | 10.3.20.1 | Splunk (web 8000, REST 8089, receiver 9997) | SSH |
| ar-linux | 10.3.20.2 | Ubuntu target, Splunk forwarder | SSH |
| ar-windows | 10.3.20.3 | Windows Server 2022 target, Splunk forwarder | WinRM HTTPS 5986, RDP, SMB |
| kali | 10.3.20.4 | Lab tools VM | SSH |
| router | 10.3.20.254 | Range router | none needed |

- Logins come from `GET /range/ansibleinventory` (`ansible_user` and
  `ansible_ssh_pass` per host: `localuser` on ar-splunk, ar-linux, and
  ar-windows, `kali` on kali). You are approved to access all range
  passwords. They are not sensitive: you may print them, and store them in
  run folders, logs, or files on `ttl-agents`.
- Run lab tools from `kali` over SSH. Keep `ttl-agents` for
  orchestration and recording.
- Splunk admin login: `admin` / `changeme123!`. Web is plain HTTP at
  `http://10.3.20.1:8000`. The REST API is HTTPS on 8089 with a self-signed
  certificate, for example
  `curl -sk -u 'admin:changeme123!' https://10.3.20.1:8089/services/search/jobs/export -d search='| metadata type=hosts index=*' -d output_mode=csv`.
- Windows events are in index `win` (sourcetype `XmlWinEventLog`) under host
  `THREATTRAILS-MV`, the 15-character NetBIOS name, not `ar-windows`.

## Runs

Put each run in `~/runs/<YYYY-MM-DD>-<short-name>/`:

- `README.md`: goal, test identifier (if applicable), lab host, and the start
  and end time in UTC.
- `commands.md`: every command exactly as run, with the host it ran on and a
  UTC timestamp.
- `outputs/`: raw output of each command.
- `splunk/`: each search you ran and its results.

Range VM passwords may appear in runs. Leave out broker tokens and any
Ludus or Proxmox credentials.
