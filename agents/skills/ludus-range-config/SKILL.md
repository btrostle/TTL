---
name: ludus-range-config
description: Read, edit, and validate the ThreatTrails-MVP Ludus range config YAML (VMs, domains, networking, router, testing, roles). Use when asked to change what the range contains or how it is networked, or to review a range config.
---

# Ludus range config

The config for `ThreatTrails-MVP` is kept in the TTL repo at
`deploy/ranges/ThreatTrails-MVP.yml`. The live copy is on Ludus. Call the
broker as the `ludus-api` skill describes.

## Rules for this lab

1. **The owner approves every config change.** Show the diff and wait. The
   Proxmox host is short on memory; the range budget is about 25 GB of RAM in
   total. Give the RAM total of the new config with the diff.
2. **Do not change VM sizes, the router, or remove VMs** unless the owner asks.
3. **Keep the Debian 12 `router:` section.** Without it Ludus builds the
   Debian 11 router, which no longer builds.
4. **Roles must be installed globally** by the owner. Check `GET /ansible`
   before you add a role. The broker's Ludus user cannot install roles (403).
5. **Templates must exist.** Check `GET /templates` before you use one.

## Ludus config rules

1. Start configs with the schema header:
   ```yaml
   # yaml-language-server: $schema=https://docs.ludus.cloud/schemas/range-config.json
   ```
2. Use `{{ range_id }}` in `vm_name` and `hostname`. It resolves to
   `ThreatTrails-MVP`.
3. Windows hostnames are 15 characters at most (NETBIOS).
4. VLANs are 2-255 and become the third octet of the IP (vlan 20 = 10.X.20.Y).
5. `ip_last_octet` is unique within a VLAN.
6. Set `linux: true` for Linux VMs, the `windows:` key for Windows VMs,
   `macOS: true` for macOS VMs.
7. Domain roles are `primary-dc`, `alt-dc`, or `member`.
8. `role_vars` is a dictionary. Do not prefix variables with hyphens.

## Workflow

1. Read the live config: `GET /range/config` with `rangeID=ThreatTrails-MVP`.
   Compare it with the repo copy and report any difference.
2. Make the change in small steps. Check it against `references/schema.md`.
3. Check templates and roles (rules 4 and 5).
4. Show the owner the diff and the RAM total. Wait for approval.
5. Upload: `PUT /range/config` with `rangeID`, the YAML in `file_text`, and
   `body` `{"force": "false"}`. Read it back with `GET /range/config` and
   compare.
6. Update `deploy/ranges/ThreatTrails-MVP.yml` to match.
7. A config change takes effect on the next deploy. Use the `ludus-deploy`
   skill, which needs the owner's go-ahead.

## References

- `references/schema.md`: full schema, valid values, defaults, and examples
  (upstream, unchanged).
- https://docs.ludus.cloud/docs/configuration
- https://docs.ludus.cloud/schemas/range-config.json

Adapted from `range-config` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
