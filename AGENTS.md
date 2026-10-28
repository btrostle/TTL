# Agent Rules

## Boundaries

No agent may reach:

1. The owner's home network outside the dev VLAN.
2. The Ludus or Proxmox management interface, or credentials from it. Agents
   use Ludus only through the Ludus MCP. The MCP holds the Ludus key and allows
   everything except operations that return Ludus or Proxmox credentials.

Inside the lab, agents may do anything.

## Working

- Keep it simple. Build the smallest thing that works, then improve it.
- Never commit or print secrets.
