# Ranges

Three test ranges, each built for one kind of attack telemetry, plus
`TTL-SIEM`, which is always on. Only one test range runs at a time, and each
must stay under the 45 GB RAM soft cap. All of them send telemetry to the one
Elastic stack on TTL-SIEM (Elastic Defend in detect mode, Basic license,
prebuilt SIEM rules), so records from every test survive range teardowns.

| Range | Config | Purpose | VLANs | RAM |
|---|---|---|---|---|
| `TTL-SIEM` | `deploy/ludus/ranges/TTL-SIEM.yml` | Shared Elastic and future shared infrastructure; always on | 100 | 9 GB |
| `TTL-MAL` | `deploy/ludus/ranges/TTL-MAL.yml` | Malware analysis | 110 dynamic, 120 static | 17 GB |
| `TTL-WKS` | `deploy/ludus/ranges/TTL-WKS.yml` | Basic AD, workstation attacks | 130, kali 139 | 27 GB |
| `TTL-AD` | `deploy/ludus/ranges/TTL-AD.yml` | Full GOAD | 140, kali 149 | 29 GB |

Each range has its own block of VLANs (100s, in tens), so an address
like `10.S.130.x` tells you the range at a glance. Never use 10 or 20:
those are the home network's VLANs. A new range takes the next free
block.

## Home network isolation (all ranges)

Two layers keep range traffic off the owner's home network. Agents have
root on range routers and can upload range configs, so the range router
alone is not enough.

1. **Range router.** Every range config sets
   `network.always_blocked_networks` to `192.168.0.0/16` and
   `172.16.0.0/12`. Ranges use `10.<n>.0.0/16`, so nothing in a range needs
   those networks. Agents must keep this block.
2. **Ludus host.** Range routers reach the internet through the host's NAT
   bridge (`vmbr1000`, 192.0.2.0/24). An nftables firewall on the host drops
   traffic from that bridge to private networks, and allows to the host
   itself only DHCP and DNS. Agents cannot reach the host, so this layer
   holds even if a range router is compromised. The owner installs it from
   `deploy/ludus/host-guard/`, which has the rules, install steps and the
   check. The same guard drops direct traffic between range routers on
   that bridge, except to TTL-SIEM's Fleet and Elasticsearch ports.

Verify layer 2 from a range router (see `deploy/ludus/host-guard/`): home
addresses, the Proxmox UI and the Ludus API must be unreachable, and the
internet reachable. Templates that use Packer's HTTP server must be built
through `ttl-template-window.sh`.

## TTL-SIEM: shared Elastic

Other ranges reach TTL-SIEM only through its router's WAN address,
`192.0.2.(100+S)` where S is TTL-SIEM's range number, on TCP 8220 (Fleet)
and 9200 (Elasticsearch). The router forwards those ports to Elastic at
`10.S.100.2` using `router.iptables_commands`, the one approved use of that
setting. The Ludus host guard allows range routers to reach TTL-SIEM on
those two ports and nothing else. Kibana (5601) is reachable only over
WireGuard from ttl-agents. A sample or attacker inside a test range can
therefore reach Fleet and Elasticsearch, which need an enrollment token or
API key; this is the same exposure a per-range Elastic had.

Elastic sees each range's events arrive from that range's router address,
and each range enrolls with its own agent policy, so every event is tagged
by range.

The `elastic` superuser can log in over 9200 too, so TTL-SIEM never uses
the role's default password. Its config has a `TTL_SIEM_ELASTIC_PASSWORD`
placeholder: replace it with a strong random password at upload, store
the password on ttl-agents outside the repo, and never commit or print it.

Never put TTL-SIEM in testing mode, and don't destroy it: it holds the
records of every run.

### Secrets file on ttl-agents

The agents keep TTL-SIEM's address and secrets in
`~/.config/ttl/siem.env` (mode 600, never committed or printed).
`upload-config.py` fills range config placeholders from it, and `esql.py`
reads the Elasticsearch address and password from it:

```sh
TTL_SIEM_ELASTIC_PASSWORD=...   # generated before TTL-SIEM's first deploy
TTL_SIEM_WAN=192.0.2.1xx        # 192.0.2.(100+S)
TTL_SIEM_ES=https://10.S.100.2:9200
TTL_MAL_ENROLLMENT_TOKEN=...
TTL_WKS_ENROLLMENT_TOKEN=...
TTL_AD_ENROLLMENT_TOKEN=...
```

Before TTL-SIEM's first deploy, generate the password without printing
it, for example
`umask 077; printf 'TTL_SIEM_ELASTIC_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> ~/.config/ttl/siem.env`.

### After deploying TTL-SIEM

The `ludus_elastic_container` role registers Fleet and the Elasticsearch
output at `10.S.100.2`, and agents switch to those URLs after enrolling.
Other ranges cannot route there. From ttl-agents, run:

```sh
python3 ~/ttl/siem-fleet-setup.py
```

It is safe to re-run, and after any TTL-SIEM rebuild it must be. It:

1. adds Fleet Server host and Elasticsearch output `ttl-siem-wan`
   (`https://192.0.2.(100+S):8220` and `:9200`, certificate checks off
   because the certificates are self-signed for `10.S.100.2`) and makes
   both the defaults. Elastic's Basic licence has no per-policy outputs,
   so every agent, including Elastic's own Fleet Server, uses the WAN
   address; the router's hairpin rules bring Elastic's own traffic back;
2. copies the role's `Ludus-Agent-Policy` (Elastic Defend in detect mode,
   the Windows and System integrations) once per test range: `TTL-MAL`,
   `TTL-WKS`, `TTL-AD`, with namespaces `ttl_mal`, `ttl_wks`, `ttl_ad` on
   the policy and every integration;
3. writes each policy's enrollment token to `siem.env`.

The owner also sets `siem_wan` in the host guard to `192.0.2.(100+S)` and
reloads it (see `deploy/ludus/host-guard/`), and assigns TTL-SIEM to both
Ludus users (see Owner setup).

### Changes from the Ludus defaults

Anything changed from what Ludus or its roles set up by default is listed
here, so a rebuild can repeat it.

- TTL-SIEM's router: `iptables_commands` forwarding 8220/9200 from
  other ranges, plus the hairpin for Elastic itself (`TTL-SIEM.yml`).
- Elastic superuser password: a generated one instead of the role's
  `elasticpassword` (`TTL_SIEM_ELASTIC_PASSWORD` in `siem.env`). If it is
  ever changed in Elasticsearch directly, re-upload the TTL-SIEM config
  so Ludus holds the same value.
- Fleet: default Fleet Server host `ttl-siem-wan` (WAN address); the
  preconfigured default output's address changed in
  `/opt/elastic_container/kibana.yml` on the Elastic VM (Kibana refuses
  API changes to it), which a redeploy of that VM overwrites; per-range copies of `Ludus-Agent-Policy` with their own namespaces
  (`siem-fleet-setup.py`, which also checks their Elastic Defend settings
  match the source). `Ludus-Agent-Policy` itself is left as is and unused.
- Ludus appends `iptables_commands` again on every router deploy without
  removing the old ones, so rules pile up as duplicates. Harmless.
- Test ranges: no Elastic VM; `ludus_elastic_agent` points at TTL-SIEM
  through `global_role_vars`.
- TTL-MAL's static and dynamic VMs get their tools from our own role,
  `deploy/ludus/roles/ttl_re_tools`, installed globally by the owner
  (`ludus ansible role add -d <path to the role>`, as an admin, then make
  it global). FLARE-VM was dropped: its template build kept failing, and
  it installs far more than needed. (Edits made while trying it, the build
  VM's RAM and the `ludus_flarevm` role's retry count, are left on the
  host unused.)
- Templates the owner builds must be moved to the Proxmox `SHARED` pool
  before the broker's user can see them.
- Host: the range guard (`deploy/ludus/host-guard/`).

### Deploying a test range

Each test range config has two placeholders under `global_role_vars`.
Before uploading the config, replace `TTL_SIEM_WAN` with `192.0.2.(100+S)`
and `TTL_<RANGE>_ENROLLMENT_TOKEN` with that range's token. Never commit
the filled-in config. After deploy, check in Fleet that every agent is
healthy under the range's policy.

## Owner setup (all ranges)

- Add the range IDs, including `TTL-SIEM`, to `LUDUS_ALLOWED_RANGES` on
  the broker.
- Install `badsectorlabs.ludus_elastic_container` and
  `badsectorlabs.ludus_elastic_agent` globally as the Ludus admin.
- Build any missing templates. Check them with `GET /templates`.
  - `TTL-SIEM`: `debian-12-x64-server-template`
  - `TTL-MAL`: `win11-22h2-x64-enterprise-template`,
    `debian-12-x64-server-template`
  - `TTL-WKS`: `win2022-server-x64-template`, `win11-22h2-x64-enterprise-template`,
    `ubuntu-22.04-x64-server-template`, `kali-x64-desktop-template`
  - `TTL-AD`: `win2019-server-x64-template`, `win2016-server-x64-template`,
    `kali-x64-desktop-template`

After that, agents create the range (`POST /ranges/create`). The owner
then assigns it to both Ludus users, which the broker blocks agents from
doing: the broker's user (`ludus range assign <broker user> <range>`) and
ttl-agents' WireGuard user (`ludus range assign <tunnel user> <range>`).
The owner or a coding agent (as root on ttl-agents) also adds the range's
`10.S.0.0/16` to `AllowedIPs` in ttl-agents' WireGuard config and restarts
it. Then agents upload the config and deploy through the
broker. TTL-SIEM comes first.

Elastic Defend runs in **detect** mode, not prevent. The Elastic role sets
this; check it in Kibana > Fleet after changing any policy.

## TTL-MAL: malware analysis

Follows OALabs' two-VM setup, plus Elastic on the dynamic VM.

| VM | VLAN.IP | Network | Role |
|---|---|---|---|
| static | 120.20 | Internet, always | Analysis tools, WSL, notes. Samples are stored but never run |
| dynamic | 110.21 | None while testing (Elastic only) | Same tools plus x64dbg, Procmon, System Informer, and Elastic Agent. Samples run here |

Both VMs get their tools from our role `ttl_re_tools`
(`ttl_re_tools_profile: static` or `dynamic`).

**Dynamic's network, enforced by the range router** (a sample with admin
can't change it):

- In from WireGuard (the owner, ttl-agents): RDP and WinRM only. No SMB.
- Out: nothing to WireGuard clients (Ludus default, stated in the
  config), nothing to static (the VLANs reject each other), no internet in
  testing mode, and TTL-SIEM's Fleet and Elasticsearch ports only.
- Files go in over WinRM (`evil-winrm` `upload`, or PowerShell
  `Copy-Item -ToSession`), and only while dynamic is clean, before a
  sample runs. The network can't tell clean from dirty; this rule can.
- RDP to dynamic with drive and clipboard redirection off, so a running
  sample can't reach your files or clipboard.

Testing mode is the dynamic VM's network switch and its reset: entering
it snapshots dynamic and blocks its internet (static has
`block_internet: false`, so it stays online), and leaving it reverts
dynamic. Samples run only in testing mode. Outside testing mode, dynamic
has internet for setup and updates only.

### After deploy (internet still on)

1. Both: check the "Report anything that did not install" task in the
   deploy log.
2. Both, by hand (owner): install IDA Free and Binary Ninja Free with your
   own downloads. On static, the WSL distro: `wsl --set-default-version 1`,
   `wsl --install -d Ubuntu-24.04`, then in Ubuntu
   `sudo apt install vim gcc make mingw-w64`.
3. Check in Fleet that dynamic is healthy under the `TTL-MAL` policy.

### Each session

1. Static: download the sample (password-protected zip) into
   `C:\samples` and do the static analysis. Never run it here.
2. Enter testing mode (dynamic is snapshotted, so it is clean). Allow
   TTL-SIEM through it (`POST /testing/allow` with `192.0.2.(100+S)`) if
   Elastic stops receiving events. From dynamic, check: no internet,
   TTL-SIEM still receives events. Stop if a check fails.
3. Copy the sample to dynamic over WinRM, into `C:\samples`. This is the
   last transfer of the session.
4. Dynamic: run and debug it with x64dbg, Procmon and System Informer.
   Results leave through Elastic and your notes, not by copying files out.
5. Collect Elastic alerts and events (ES|QL, namespace `ttl_mal`) and
   notes into the run folder. Read tool output on screen or through WinRM
   commands; don't copy files off dynamic.
6. Leave testing mode. Dynamic reverts; the events stay in TTL-SIEM.

## TTL-WKS: basic AD

`ttl.lab` with DC01 (Server 2022), WS01 and WS02 (Windows 11), and an
Ubuntu server on VLAN 130, all running Defend, with kali on VLAN 139.
A GPO disables
Microsoft Defender so attack tools run. The Linux server is not joined to the
domain. Add SSSD/realmd as a setup step if a test needs it.

## TTL-AD: full GOAD

The five GOAD VMs use the names, templates and IPs from GOAD's Ludus
provider config, on VLAN 140 instead of GOAD's 10 (kali on 149). Deploy
the VMs through the broker, then run GOAD's Ansible playbooks from kali
with a static inventory of the range IPs, with `ip_range` set to
`10.X.140`. Do not run
`goad.sh -p ludus`: it calls the Ludus API with its own key, which the lab
boundary forbids. The GOAD playbooks rename hosts and build the domains
after Elastic Agent is installed. Check in Fleet that every host
reports under its GOAD name.
