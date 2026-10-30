---
name: ludus-api
description: Call Ludus through the TTL broker. Use when you need range status, config, logs, power, testing mode, snapshots, templates, Ansible roles, or blueprints, or when a Ludus doc or user gives a `ludus` CLI command that you must turn into a broker call.
---

# Ludus through the broker

There is no `ludus` CLI or Ludus API key on this box. Every Ludus action is one
call to the broker, which holds the key and forwards an allowlisted part of the
Ludus API v2.

## How to call it

- Claude Code and Codex: the `ludus` MCP server. `list_operations` shows what is
  allowed. `ludus_request` makes a call.
- pi and scripts: `python3 ~/ttl/mcpcall.py '<json arguments>'`.

Both take the same arguments:

```json
{"method": "GET", "path": "/range", "query": {"rangeID": "ThreatTrails-MVP"}}
```

- `path` is relative to `/api/v2`, with no query string.
- `query` holds `rangeID` and other query parameters.
- `body` is the JSON body.
- `file_text` is for `PUT /range/config` only: the YAML text, with form fields
  such as `force` in `body`.

Every range operation needs `rangeID=ThreatTrails-MVP`. Other ranges are
refused. Do not pass `userID`; the broker refuses it.

## Rules

- `list_operations` is the source of truth for what the broker allows. If it
  and `references/operations.md` disagree, follow `list_operations`. If an
  operation is not listed, it is blocked. Do not look for a way around it.
- Use `references/operations.md` only to turn a `ludus` CLI command into a
  broker call.
- Field names come from `GET /openapi`. Check it before you send a body you
  have not sent before.
- Ask the owner before you deploy, power on, delete VMs, or roll back
  snapshots. See the `ludus-deploy` skill for deploys.
- `GET /range/ansibleinventory` returns range VM passwords. Use them, but never
  print or save them.
- A 403 from Ludus means the broker's Ludus user lacks that right (for example
  installing Ansible roles). Report it to the owner.

## References

- `references/operations.md`: CLI commands mapped to broker calls, and what is
  blocked.
- Ludus API docs: https://docs.ludus.cloud/docs/api

Adapted from `ludus-cli` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
