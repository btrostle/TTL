---
name: ludus-deploy
description: Deploy, rebuild, or repair a TTL Ludus range (TTL-SIEM, TTL-MAL, TTL-WKS, TTL-AD) through the broker. Use when asked to deploy, redeploy, rebuild, or fix a range in ERROR state.
---

# Deploying a TTL range

The owner grants standing authorization for range VM deploys, power-on, and
deletion without further approval. Deploys load a Proxmox host that is short
on memory and must not run close to the 02:00 host-time backup. Only one
test range runs at a time, next to TTL-SIEM: power off or delete the
previous test range before you deploy another.

TTL-SIEM comes first. Test ranges send telemetry to it, and their configs
need its address and enrollment tokens (see `~/ttl/ranges.md`, "After
deploying TTL-SIEM"). Never rebuild or delete TTL-SIEM without the owner:
it holds every run's records.

## Steps

1. Read the state: `GET /range` with `rangeID=<range>`. Note
   `rangeState` and the VM list. A range that doesn't exist yet needs
   `POST /ranges/create` first.
2. Upload the config: `python3 ~/ttl/upload-config.py <range> --check`,
   then without `--check`. It must report that the live config matches.
3. To rebuild from scratch, `DELETE /range/<range>/vms`, then poll
   `GET /range` until `rangeState` is `DESTROYED` with no VMs. Do not use
   plain `DELETE /range`: it refuses while VMs exist and removes more than a
   rebuild needs.
4. Deploy: `POST /range/deploy` with `rangeID` and body `{}` for all VMs, or
   `{"limit": "<range>-<vm>"}` for one VM. `limit` takes a VM name;
   `localhost` matches nothing.
5. Poll `GET /range` every 30 seconds until `rangeState` is no longer
   `DEPLOYING` or `WAITING`.
6. Read `GET /range/logs` through `grep` only: it holds the filled secrets
   (see the agent rules). Look for `fatal:` and `ERROR!` lines, skipping
   ones followed by `...ignoring`, and read the `PLAY RECAP`. Older runs:
   `GET /range/logs/history`, then `GET /range/logs/history/{logID}`.
7. Check the result: every VM on its static IP. For a test range, every
   VM with the `ludus_elastic_agent` role shows as healthy in Kibana >
   Fleet under the range's policy, and `esql.py` returns recent events in
   its namespace. For TTL-SIEM, follow "After deploying TTL-SIEM" in
   `~/ttl/ranges.md`.

`ERROR` stays until a deploy succeeds, even if a limited deploy fixed the
cause.

## Known failures

- **"Wait for VM to acquire an IP address" with `JSONDecodeError`** on a fresh
  build: Ludus polls the guest agent before it is up. Rerun the full deploy.
  Each run gets at least one VM further. Stop and report if a run makes no
  progress.
- **"role ... was not found"**: the role is not installed globally. The broker
  blocks role installs. Ask the owner to run
  `ludus ansible role add <role> --global`.
- **Router package install 404 from `security.debian.org`**: the range is
  using the Debian 11 router. The config must have the Debian 12 `router:`
  section; ask the owner if it is missing.
## Config

Range configs live in the TTL repo (`deploy/ludus/ranges/<range>.yml`),
installed on this box in `~/ttl/ranges/`. Do not change VM sizes or the
router without the owner.
