---
name: ludus-range-config
description: Read, edit, and validate a TTL Ludus range config YAML (VMs, domains, networking, router, testing, roles). Use when asked to change what the range contains or how it is networked, or to review a range config.
---

# Ludus range config

Each range's config is kept in the TTL repo at
`deploy/ludus/ranges/<range>.yml`, installed on this box in `~/ttl/ranges/`.
The live copy is on Ludus. Call the broker as the `ludus-api` skill
describes.

The repo configs hold placeholders for secrets and addresses
(`TTL_SIEM_WAN`, `TTL_SIEM_ELASTIC_PASSWORD`, `TTL_<RANGE>_ENROLLMENT_TOKEN`).
Keep them as placeholders in every file you edit or show.

## Rules for this lab

1. **The owner approves every config change.** Show the diff and wait. The
   Proxmox host is short on memory; the range budget is a 45 GB RAM soft
   cap, with one range up at a time. Give the RAM total of the new config
   with the diff.
2. **Do not change VM sizes, the router, or remove VMs** unless the owner asks.
3. **Keep the Debian 12 `router:` section.** Without it Ludus builds the
   Debian 11 router, which no longer builds.
4. **Roles must be installed globally** by the owner. Check `GET /ansible`
   before you add a role. The broker blocks role installs; report a missing
   role to the owner.
5. **Templates must exist.** Check `GET /templates` before you use one.
6. **Keep `network.always_blocked_networks`** with `192.168.0.0/16` and
   `172.16.0.0/12` in every range config. It is layer 1 of the home-network
   block (see AGENTS.md). Never remove or narrow it, and never add
   `router.iptables_commands` or rules that reach private networks outside
   `10.0.0.0/8`. The only exception is TTL-SIEM's router
   `iptables_commands`, which must stay exactly as committed. Before
   uploading, check that the block is still there.
7. **Keep the Elastic wiring.** Test ranges keep `global_role_vars` with
   the Fleet URL and enrollment token placeholders. Agents use the
   `badsectorlabs.ludus_elastic_agent` role with no `depends_on`. No test
   range gets its own Elastic VM.

## Ludus config rules

1. Start configs with the schema header:
   ```yaml
   # yaml-language-server: $schema=https://docs.ludus.cloud/schemas/range-config.json
   ```
2. Use `{{ range_id }}` in `vm_name` and `hostname`. It resolves to
   `<range>`.
3. Windows hostnames are 15 characters at most (NETBIOS).
4. VLANs are 2-255 and become the third octet of the IP (vlan 20 = 10.X.20.Y).
5. `ip_last_octet` is unique within a VLAN.
6. Set `linux: true` for Linux VMs, the `windows:` key for Windows VMs,
   `macOS: true` for macOS VMs.
7. Domain roles are `primary-dc`, `alt-dc`, or `member`.
8. `role_vars` is a dictionary. Do not prefix variables with hyphens.

## Workflow

1. Read the live config: `GET /range/config` with `rangeID=<range>`.
   Compare it with the repo copy and report any difference. The live copy
   has the secrets filled in: compare it in a script, and don't print it.
2. Make the change in small steps. Check it against `references/schema.md`.
3. Check templates and roles (rules 4 and 5).
4. Show the owner the diff and the RAM total. Wait for approval.
5. Write the change to `~/ttl/ranges/<range>.yml` (placeholders intact),
   then upload with `python3 ~/ttl/upload-config.py <range>`. It reads the
   config back and reports whether it matches.
6. Give the owner the diff to commit to `deploy/ludus/ranges/<range>.yml`.
7. A config change takes effect on the next deploy. Use the `ludus-deploy`
   skill, which needs the owner's go-ahead.

## References

- `references/schema.md`: full schema, valid values, defaults, and examples
  (upstream, unchanged).
- https://docs.ludus.cloud/docs/configuration
- https://docs.ludus.cloud/schemas/range-config.json

Adapted from `range-config` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
