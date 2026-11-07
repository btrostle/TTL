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
{"method": "GET", "path": "/range", "query": {"rangeID": "TTL-MAL"}}
```

- `path` is relative to `/api/v2`, with no query string.
- `query` holds `rangeID` and other query parameters.
- `body` is the JSON body.
- `file_text` is for `PUT /range/config` only: the YAML text, with form fields
  such as `force` in `body`.

Every range operation needs `rangeID` set to the range you are working on
(`TTL-SIEM`, `TTL-MAL`, `TTL-WKS`, `TTL-AD`; see AGENTS.md). The broker
refuses ranges that are not on its allowlist. Do not pass `userID`; the
broker refuses it. VM names are `<rangeID>-<vm>`, for example
`TTL-MAL-dynamic`.

## Rules

- `list_operations` is the source of truth for what the broker allows. If it
  and `references/operations.md` disagree, follow `list_operations`. If an
  operation is not listed, it is blocked. Do not look for a way around it.
- Use `references/operations.md` only to turn a `ludus` CLI command into a
  broker call.
- Field names come from `GET /openapi`. Check it before you send a body you
  have not sent before.
- Deploying, powering on, and deleting range VMs have standing owner
  authorization; no further approval is needed. Ask before rolling back
  snapshots. See the `ludus-deploy` skill for deploys.
- Upload range configs with `python3 ~/ttl/upload-config.py <range>`,
  not with a direct `PUT /range/config`: the configs hold secret
  placeholders that the script fills without printing them.
- `GET /range/config` for a range that has been uploaded returns the
  filled config, including tokens and the Elastic password. Don't print it
  or save it to a run folder.
- `GET /range/ansibleinventory` returns range VM passwords. They are not
  sensitive: you may use, print, and save them.
- Roles, collections, and templates are the owner's. Report anything to
  install or delete; do not try to do it yourself.
- A 403 from Ludus means the broker's Ludus user lacks that right. Report it
  to the owner.

## References

- `references/operations.md`: CLI commands mapped to broker calls, and what is
  blocked.
- Ludus API docs: https://docs.ludus.cloud/docs/api

Adapted from `ludus-cli` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
