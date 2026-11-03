---
name: ludus-troubleshooting
description: Diagnose ThreatTrails-MVP Ludus deploy, template, network, WinRM, and Ansible failures through the broker. Use when a deploy or template build fails, the range is in ERROR, or a range VM is unreachable.
---

# Ludus troubleshooting

You can see Ludus only through the broker (the `ludus-api` skill) and the range
VMs over the tunnel. You cannot reach the Ludus or Proxmox host. A fix that
needs a root shell on that host is the owner's: report it, with the evidence
and the doc link, and do not try to do it another way.

## Workflow

1. Get the exact error text.
2. Range state: `GET /range` with `rangeID=ThreatTrails-MVP`. Note
   `rangeState`, `testingEnabled`, and each VM's power state.
3. Errors: `GET /range/logs`. Search for `fatal:` and `ERROR!`, skipping
   lines followed by `...ignoring`. Read the `PLAY RECAP`. For older runs use
   `GET /range/logs/history` and `GET /range/logs/history/{logID}`.
4. Match the error to `references/common-errors.md`. The `ludus-deploy` skill
   lists failures already seen on this range; check it first.
5. Check the config: `GET /range/config`. Templates: `GET /templates/status`.
   Roles: `GET /ansible`.
6. Check the VM itself from `kali` or `ttl-agents`: ping, SSH (Linux) or
   WinRM HTTPS 5986 (Windows).
7. Fix what you can through the broker or on the range VMs. Ask the owner
   before a redeploy (see `ludus-deploy`).
8. Confirm the fix: the range reaches `SUCCESS` and the VM answers.

## Common patterns

- Ludus actions are idempotent. A failed deploy often succeeds when rerun.
- Rerun only what failed: `tags` (`network`, `user-defined-roles`,
  `custom-groups`, `share`), `only_roles`, or `limit` with a VM name.
- `ERROR` stays until a deploy succeeds, even if a limited deploy fixed the
  cause.
- Ansible failures often involve WinRM (Windows) or SSH (Linux).
- Domain join failures are usually DNS order or timing.
- Network and template download failures on the host (dnsmasq, NAT bridge,
  disk space) are the owner's.

## References

- `references/common-errors.md`: known errors, causes, and fixes, marked by
  who can do them.
- https://docs.ludus.cloud/docs/troubleshooting/client
- https://docs.ludus.cloud/docs/troubleshooting/network/

Adapted from `troubleshooting` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
