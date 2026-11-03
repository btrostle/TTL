# Agent Rules

## Authorization

The owner authorizes security testing of VMs in the ThreatTrails homelab
range. Agents may carry out assigned tests within that range. This
authorization does not extend to the owner's home network or the Ludus and
Proxmox management interfaces.

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
  Agents are approved to fetch, use, print, and store them. The Splunk
  admin login is documented in `agents/AGENTS.md`.
- This repository is public. Do not commit home network details (subnets,
  host IPs, firewall rules, known gaps). Put them in `private/`, which is
  gitignored. Lab notes for the owner are in `private/network-context.md`.
