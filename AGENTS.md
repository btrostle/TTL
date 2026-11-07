# Agent Rules

These rules are for coding agents working on this repository. Lab operations
agents get `deploy/agents/` instead, installed on `ttl-agents` by
`deploy/agents/agent-config.sh`.

## Authorization

The owner authorizes security testing of VMs in the ThreatTrails homelab
range. Agents may carry out assigned tests and deploy, power on, or delete
range VMs without further approval. Agents may use sudo/root and Windows
Administrator inside range VMs. The no-sudo restriction applies only to the
`ttl-agents` orchestration host. This authorization does not extend to the
owner's home network or the Ludus and Proxmox management interfaces.

## Boundaries

No agent may reach:

1. The owner's home network outside the dev VLAN.
2. The Ludus or Proxmox management interface, or credentials from it. Agents
   use Ludus only through the Ludus MCP. The MCP holds the Ludus key and allows
   everything except operations that return Ludus or Proxmox credentials.
   All Ludus work runs on `ttl-agents` through its broker connection, never
   from another host or with another Ludus key.

Inside the lab, agents may carry out assigned security tests.

## Working

- Keep it simple. Build the smallest thing that works, then improve it.
- Never commit or print secrets.
- Range VM passwords (from `GET /range/ansibleinventory`) are not sensitive.
  Agents are approved to fetch, use, print, and store them. The TTL-SIEM
  Elastic password and enrollment tokens are secrets: they live only in
  `~/.config/ttl/siem.env` on ttl-agents (see `docs/ranges.md`).
- Record every command you run (or ask the owner to run) to build or change
  the lab outside the repo's scripts in `private/build-log.md`: where it
  ran, the command, and why, plus any gotcha. Never record secret values;
  note how they were generated or where they're stored. Once the lab is
  built out, this log is the basis for consolidating the whole build into
  a simple, repeatable deploy. Prefer steps that can be scripted.
- This repository is public. Do not commit home network details (subnets,
  host IPs, firewall rules, known gaps). Put them in `private/`, which is
  gitignored. Lab notes for the owner are in `private/network-context.md`.
