# Ludus CLI to broker calls

Each row shows a `ludus` CLI command and the broker call that does the same
thing. This table helps with translation only. What the broker allows is what
`list_operations` returns; if the two disagree, `list_operations` is right. `R` means `"query": {"rangeID": "ThreatTrails-MVP"}`. Field names are
from the Ludus API v2.1 OpenAPI spec; check `GET /openapi` if a call fails.

## Table of Contents

- [Range](#range)
- [Power](#power)
- [Testing mode](#testing-mode)
- [Snapshots](#snapshots)
- [Templates](#templates)
- [Ansible](#ansible)
- [Blueprints](#blueprints)
- [Blocked](#blocked)

## Range

| CLI | Broker call |
|---|---|
| `ludus range list` | `GET /range`, R. Add `"details": true` to `query` for more |
| `ludus range accessible` | `GET /ranges/accessible` |
| `ludus range config get` | `GET /range/config`, R |
| `ludus range config get example` | `GET /range/config/example` |
| `ludus range config set -f x.yml` | `PUT /range/config`, R, `file_text`: the YAML, `body`: `{"force": "false"}` |
| `ludus range deploy` | `POST /range/deploy`, R, `body`: `{}` |
| `ludus range deploy -t network` | `POST /range/deploy`, R, `body`: `{"tags": "network"}` |
| `ludus range deploy --only-roles a,b` | `POST /range/deploy`, R, `body`: `{"only_roles": ["a", "b"]}` |
| `ludus range deploy -l VM` | `POST /range/deploy`, R, `body`: `{"limit": "ThreatTrails-MVP-<vm>"}` |
| `ludus range deploy --force` | add `"force": true` to the deploy body (deploys while testing mode is on) |
| `ludus range logs` | `GET /range/logs`, R. Add `"tail": 50` to `query` for the last lines |
| `ludus range errors` | No API call. Read `GET /range/logs` and search for `fatal:` and `ERROR!`, skipping lines followed by `...ignoring` |
| `ludus range taskoutput "<task>"` | No API call. Search `GET /range/logs` for the task name |
| `ludus range abort` | `POST /range/abort`, R |
| `ludus range rm` | `DELETE /range/ThreatTrails-MVP/vms`. Ask the owner first |
| `ludus range inventory` | `GET /range/ansibleinventory`, R. Contains passwords |
| `ludus range etc-hosts` | `GET /range/etchosts`, R |
| `ludus range rdp` | `GET /range/rdpconfigs`, R (zip, returned base64) |
| `ludus range gettags` | `GET /range/tags` |
| Log history | `GET /range/logs/history`, R, then `GET /range/logs/history/{logID}`, R |

Do not use `DELETE /range`. It refuses while VMs exist and removes the range
itself, not only its VMs.

## Power

| CLI | Broker call |
|---|---|
| `ludus power on` | `PUT /range/poweron`, R, `body`: `{"machines": ["all"]}` or VM names. Ask the owner first |
| `ludus power off` | `PUT /range/poweroff`, R, `body`: `{"machines": ["all"]}` or VM names |

Auto-shutdown (`GET`/`PUT /range/auto-shutdown`) is allowed by the broker but
the plugin is not loaded on this Ludus server. Power off by hand.

## Testing mode

| CLI | Broker call |
|---|---|
| `ludus testing status` | `GET /range`, R. Read `testingEnabled` and the allowed lists |
| `ludus testing start` | `PUT /testing/start`, R |
| `ludus testing stop` | `PUT /testing/stop`, R. Reverts the testing snapshot |
| `ludus testing allow -d x.com` | `POST /testing/allow`, R, `body`: `{"domains": ["x.com"]}` or `{"ips": [...]}` |
| `ludus testing deny -d x.com` | `POST /testing/deny`, R, same body |
| `ludus testing update -n VM` | `POST /testing/update`, R, `body`: `{"name": "ThreatTrails-MVP-<vm>"}` (updates the VM while testing mode is on) |

## Snapshots

| CLI | Broker call |
|---|---|
| `ludus snapshots list` | `GET /snapshots/list`, R |
| `ludus snapshots create name` | `POST /snapshots/create`, R, `body`: `{"name": "...", "description": "...", "vmids": [], "includeRAM": false}` (empty `vmids` means all VMs) |
| `ludus snapshots revert name` | `POST /snapshots/rollback`, R, `body`: `{"name": "...", "vmids": []}`. Ask the owner first |
| `ludus snapshots rm name` | `POST /snapshots/remove`, R, `body`: `{"name": "...", "vmids": []}` |

## Templates

| CLI | Broker call |
|---|---|
| `ludus templates list` | `GET /templates` |
| `ludus templates status` | `GET /templates/status` |
| `ludus templates build -n a,b` | `POST /templates`, `body`: `{"templates": ["a", "b"]}`. Ask the owner first: builds load the host |
| `ludus templates logs` | `GET /templates/logs`; older runs `GET /templates/logs/history` |
| `ludus templates abort` | `POST /templates/abort` |
| `ludus templates rm -n name` | Blocked. Report the template to the owner (see below) |
| `ludus templates add -d dir` | Blocked (no upload path in the broker) |

## Ansible

| CLI | Broker call |
|---|---|
| `ludus ansible role list`, `collection list` | `GET /ansible` |
| `ludus ansible subscription-roles list` | `GET /ansible/subscription-roles` |
| `ludus ansible role add`, `collection add`, `role scope` | Allowed by the broker, but Ludus returns 403 for the broker's user. Ask the owner to install the role globally |

## Blueprints

| CLI | Broker call |
|---|---|
| `ludus blueprint list` | `GET /blueprints` |
| `ludus blueprint config get <id>` | `GET /blueprints/{blueprintID}/config` |
| `ludus blueprint create -s ThreatTrails-MVP` | `POST /blueprints/from-range`, `body`: `{"blueprintID": "...", "name": "...", "description": "...", "rangeID": "ThreatTrails-MVP"}` |
| `ludus blueprint apply <id>` | `POST /blueprints/{blueprintID}/apply`, `body`: `{"rangeID": "ThreatTrails-MVP", "force": false}`. Replaces the range config; ask the owner first |
| `ludus blueprint rm <id>` | Blocked. Report the blueprint to the owner (see below) |

Sources (`/sources/...`) are also allowed, except deleting them; see
`list_operations`.

## Blocked

These are refused by the broker. Do not try to reach them another way:

- `ludus apikey`, `users apikey`, `users wireguard`, `users creds get/set`:
  return or set Ludus or Proxmox credentials.
- `users`, `groups`, `range assign/revoke`, `range users`, blueprint
  `share`/`access`: Ludus administration.
- `vm destroy`, `diagnostics`, `migrate`, `antisandbox install-*`,
  `kms install`: Proxmox host changes.
- Deleting templates, blueprints, or sources: they are shared beyond this
  range. If one looks unused, tell the owner its name, why it can go, and what
  uses it, if anything. The owner deletes it.
- Any `-u/--user` impersonation, and any range other than `ThreatTrails-MVP`.
