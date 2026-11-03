---
name: ludus-deploy
description: Deploy, rebuild, or repair the ThreatTrails-MVP Ludus range through the broker. Use when asked to deploy, redeploy, rebuild, or fix a range in ERROR state.
---

# Deploying ThreatTrails-MVP

Ask the owner first. Deploys load a Proxmox host that is short on memory, and
must not run close to the 02:00 host-time backup.

## Steps

1. Read the state: `GET /range` with `rangeID=ThreatTrails-MVP`. Note
   `rangeState` and the VM list.
2. To rebuild from scratch, `DELETE /range/ThreatTrails-MVP/vms`, then poll
   `GET /range` until `rangeState` is `DESTROYED` with no VMs. Do not use
   plain `DELETE /range`: it refuses while VMs exist and removes more than a
   rebuild needs.
3. Deploy: `POST /range/deploy` with `rangeID` and body `{}` for all VMs, or
   `{"limit": "ThreatTrails-MVP-<vm>"}` for one VM. `limit` takes a VM name;
   `localhost` matches nothing.
4. Poll `GET /range` every 30 seconds until `rangeState` is no longer
   `DEPLOYING` or `WAITING`.
5. Read `GET /range/logs`. Look for `fatal:` and `ERROR!` lines, skipping
   ones followed by `...ignoring`, and read the `PLAY RECAP`. Older runs:
   `GET /range/logs/history`, then `GET /range/logs/history/{logID}`.
6. Check the result: every VM on its static IP (see AGENTS.md), and Splunk's
   receiver (10.3.20.1:9997) has connections from 10.3.20.2 and 10.3.20.3.

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
- **`ar-linux` "Stop splunk uf" or "splunk license acceptance" times out**
  (`Failed to stop/start SplunkForwarder.service: Connection timed out`):
  happens when rerunning the role on an existing forwarder. polkit 0.105 does
  not let `splunkfwd` manage the unit. On `ar-linux`, as root, create
  `/etc/polkit-1/localauthority/50-local.d/50-splunkfwd.pkla`:

  ```ini
  [Allow splunkfwd to manage the Splunk forwarder service]
  Identity=unix-user:splunkfwd
  Action=org.freedesktop.systemd1.manage-units
  ResultAny=yes
  ResultInactive=yes
  ResultActive=yes
  ```

  Then rerun the deploy for `ar-linux`. A fresh build does not hit this.

## Config

The range config lives in the TTL repo (`deploy/ranges/ThreatTrails-MVP.yml`).
Do not change VM sizes or the router without the owner.
