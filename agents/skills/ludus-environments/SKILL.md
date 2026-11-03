---
name: ludus-environments
description: Find and plan pre-built Ludus environments (GOAD, SCCM, ADCS, Elastic, Splunk Attack Range, Vulhub, and others) for a test in ThreatTrails-MVP. Use when a test needs a lab setup the range does not have, or when asked which environment fits a goal.
---

# Ludus environments

`references/environments.md` lists pre-built Ludus environments with their
templates, roles, resources, and config snippets. Here they are plans, not
something you can deploy on your own:

- The broker allows only one range, `ThreatTrails-MVP`. Using an environment
  means changing that range's config (the `ludus-range-config` skill).
- The Proxmox host is short on memory. The range budget is about 25 GB of RAM
  in total. Most AD environments need more (GOAD needs about 40 GB).
- Roles and collections must be installed globally by the owner. The broker
  blocks installs, including source and blueprint installs.
- Templates must already be built (`GET /templates`).

## Workflow

1. Find what the test needs: OS, domain, services, telemetry.
2. Check whether the current range already covers it (`GET /range/config`).
   Prefer adding one VM or one role to the current range over a new
   environment.
3. Pick the smallest matching environment from `references/environments.md`.
   Write down its templates, roles, collections, and RAM.
4. Check what is missing: `GET /templates` and `GET /ansible`.
5. Send the owner a short plan: what changes in the config, the RAM total,
   the roles and templates to install, and any external playbook steps.
6. After the owner approves and installs what is needed, make the config
   change with `ludus-range-config` and deploy with `ludus-deploy`.

External playbooks (for example GOAD's) run from `kali` over the range
network, not from the Ludus host.

## References

- `references/environments.md`: environment catalog (upstream, unchanged).
  Its commands use the `ludus` CLI; turn them into broker calls with the
  `ludus-api` skill.
- https://docs.ludus.cloud/docs/category/environment-guides

Adapted from `environment-guide` in https://gitlab.com/badsectorlabs/ludus-skills
(MIT, see `../LICENSE-ludus-skills`).
