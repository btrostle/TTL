# Ludus deploy notes

Lessons from rebuilding `ThreatTrails-MVP` through the broker on 2026-10-29.
Everything here was done as the broker's Ludus user (`ttlabsvc`) from
`ttl-agents`, the way an agent would do it. To review.

## Deploy sequence that works

1. `GET /range/config?rangeID=...` and keep a copy before changing anything.
2. To rebuild, `DELETE /range/{rangeID}/vms`. It removes the VMs but keeps the
   range and its config. Plain `DELETE /range` refuses with 409 "Range has VMs.
   Use --force" and would remove more than a rebuild needs.
3. Poll `GET /range?rangeID=...` until `rangeState` is `DESTROYED` with zero
   VMs.
4. `POST /range/deploy?rangeID=...` with body `{}` for a full deploy, or
   `{"limit": "<vm_name>"}` for one VM.
5. Poll `rangeState` until it leaves `DEPLOYING`/`WAITING`. Then read
   `GET /range/logs?rangeID=...` and search for `fatal:` and `ERROR!` lines,
   skipping ones followed by `...ignoring`. Older runs are in
   `GET /range/logs/history` and `GET /range/logs/history/{logID}`.

## Nuances

### Roles are per Ludus user

Ansible roles installed by one Ludus user are not visible to another. The range
was last deployed by the owner's user, so deploying as `ttlabsvc` failed with
"the role 'p4t12ick.ludus_ar_linux' was not found". `ttlabsvc` cannot install
roles itself (`POST /ansible/role` returns 403 "You are not authorized to
perform this ansible action").

Fix used: the owner installed the three `p4t12ick.ludus_ar_*` roles globally as
the Ludus admin. Any new role a range needs must be installed globally the same
way, or agents' deploys will fail.

### Debian 11 router is end of life

With no `router:` section in the range config, Ludus builds its default Debian
11 router. Debian 11 security support has ended, so the router's package
install fails with 404 from `security.debian.org`. Fix: set the router in the
range config (now in the live config):

```yaml
router:
  vm_name: "{{ range_id }}-router-debian12-x64"
  hostname: "{{ range_id }}-router"
  template: debian-12-x64-server-template
  ram_gb: 2
  cpus: 2
```

Upload the config with `PUT /range/config?rangeID=...`, passing the YAML as
`file_text` and `{"force": "false"}` as the body.

### `limit` takes a VM name, not `localhost`

`{"limit": "localhost"}` ends with "Specified inventory, host pattern and/or
--limit leaves us with no hosts to target" and does nothing. A deploy that does
nothing still leaves the range in `ERROR`. Use a VM name such as
`ThreatTrails-MVP-ar-linux`.

`limit` does not stagger VM creation. On 2026-10-30, a deploy limited to the
router after `DELETE /range/{rangeID}/vms` still cloned and started all five
VMs, because Ludus creates VMs in plays on `localhost`. Only the per-VM
configuration was limited. To space out power-on, use `PUT /range/poweron`
with one VM name at a time on VMs that already exist.

### `ERROR` sticks until a deploy succeeds

The range stays in `ERROR` after any failed deploy, even a limited one that
fixed the original problem. Only a successful deploy clears it.

### "Wait for VM to acquire an IP address" fails on fresh VMs

On a fresh build, the task fails with `JSONDecodeError: Expecting value` right
after "Start the VM". Ludus asks Proxmox for the guest agent's IP before the
agent is up and does not retry. Each rerun gets one VM further, because the
VMs it already created are kept. Rerunning the full deploy until no VM is left
to create is the workaround. A better fix would be in Ludus itself.

### Splunk forwarder on `ar-linux` (redeploy over an existing VM)

Rerunning `p4t12ick.ludus_ar_linux` on a VM that already has the forwarder
fails at "Stop splunk uf" and "splunk license acceptance" with
`Failed to stop/start SplunkForwarder.service: Connection timed out`. The role
runs `splunk stop/start` as `splunkfwd`, which asks systemd through polkit, and
nothing authorizes it. The VM has polkit 0.105, which reads `.pkla` files, not
`rules.d`.

A rule that worked on the old VM, at
`/etc/polkit-1/localauthority/50-local.d/50-splunkfwd.pkla`:

```ini
[Allow splunkfwd to manage the Splunk forwarder service]
Identity=unix-user:splunkfwd
Action=org.freedesktop.systemd1.manage-units
ResultAny=yes
ResultInactive=yes
ResultActive=yes
```

It lets `splunkfwd` manage any unit, not just the forwarder. `splunk stop` can
still hang in `deactivating` for several minutes. Whether a fresh build hits
this at all: see the result below.

### Range VM credentials

`GET /range/ansibleinventory` returns the range VMs' login and sudo passwords
(`localuser` on Linux). These are lab credentials, not Ludus management
credentials, so the broker allows them. The owner has approved agents to
access all range passwords; they are not sensitive.

### Calling the broker without an MCP client

`deploy/mcpcall.py` is a stdlib-only MCP client used for this work (copy it to
`ttl-agents`). It reads the token from `~/.config/ttl/broker.env` and calls
`ludus_request` with a JSON argument. It is the start of the `ludus` CLI pi
needs, since pi has no MCP support.

## Result of the 2026-10-29 rebuild

`SUCCESS` at 02:51 UTC, about 15 minutes after the VMs were deleted. The
sequence was:

1. The first full deploy failed on the Debian 11 router. The router was switched
   to Debian 12 and only its VM was deleted.
2. The next two deploys each failed at "Wait for VM to acquire an IP address",
   each after creating one more VM.
3. The fourth deploy created `kali` and configured all five VMs with no failed
   tasks.

The Splunk forwarder problem did not occur on the fresh `ar-linux`, which
supports the idea that it only affects reruns over an existing forwarder.

Checked afterwards from `ttl-agents`:

- All VMs are on their static addresses:
  - router at 10.3.20.254
  - `ar-splunk` at 10.3.20.1
  - `ar-linux` at 10.3.20.2
  - `ar-windows` at 10.3.20.3
  - `kali` at 10.3.20.4
- The Splunk ports are open: 8000 (web), 8089 (management) and 9997
  (receiver).
- The Splunk receiver has established forwarder connections from 10.3.20.2
  and 10.3.20.3.
- Windows answers on WinRM HTTPS (5986), RDP (3389) and SMB (445). Ludus uses
  WinRM over HTTPS, so port 5985 being closed is expected.
- SSH (22) is open on `ar-linux` and `kali`.
- Testing mode is off.

## Host froze after the rebuild

The Proxmox host (60 GB RAM) froze about 15 minutes after the deploy finished
and needed a hard reboot. The owner's investigation found:

- The range commits 42 GB with no ballooning, on top of about 58 GB already
  committed to other guests.
- The host was swapping by the time the VMs started, and the nightly vzdump
  backup at 21:00 host time pushed it over.
- `vm.swappiness` was 60 because `/etc/sysctl.conf` was not applied, and KSM
  was off.

The same range had run before at the same size. What changed was the extra
8 GB for `ttl-agents`, freshly built VMs touching all their memory during
setup, and the backup.

Lesson: the broker user cannot see host memory, so a deploy must assume the
host is tight. Size the range to fit, power it off when idle, and never deploy near the
backup window. Ludus auto-shutdown is not available here: `/range/auto-shutdown`
returns 404 "implemented in a plugin that is not loaded" (likely Ludus Pro).

## Loose ends

- Revoke the UniFi API key (still valid at last check), then delete the local
  copies in the session scratchpad.
- Dev VLAN: other Dev hosts can reach the router admin UI over IPv6 link-local.
- The range config now lives in `deploy/ranges/ThreatTrails-MVP.yml`, sized to
  25 GB (Splunk 8, Windows 6, Linux 2, Kali 8, router 1). Revisit after the
  mini PC migration.

## osquery events stamped 4 hours ahead

On 2026-10-30, `osquery:results` events from `ar-linux` were indexed 4 hours
in the future (the VM's EDT offset). The events carry `calendarTime` as UTC
text and `unixTime` as epoch seconds. Splunk had no timestamp settings for
the sourcetype, read `calendarTime`, and ignored its `UTC` suffix.

Fix, on `ar-splunk` in
`/opt/splunk/etc/apps/ttl_osquery_time/local/props.conf`, then a Splunk
restart:

```ini
[osquery:results]
TIME_PREFIX = "unixTime":
TIME_FORMAT = %s
MAX_TIMESTAMP_LOOKAHEAD = 12
```

It lives only on the VM. Rebuilding `ar-splunk` loses it until it is added to
the `p4t12ick.ludus_ar_splunk` role or reapplied by hand. Events indexed
before the fix keep their wrong times.
