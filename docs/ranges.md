# Ranges

Three test ranges, each built for one kind of attack telemetry, plus
`TTL-SIEM`, which is always on. Only one test range runs at a time, and each
must stay under the 45 GB RAM soft cap. All of them send telemetry to the one
Elastic stack on TTL-SIEM (Elastic Defend in detect mode, Basic license,
prebuilt SIEM rules), so records from every test survive range teardowns.

| Range | Config | Purpose | RAM |
|---|---|---|---|
| `TTL-SIEM` | `deploy/ludus/ranges/TTL-SIEM.yml` | Shared Elastic and future shared infrastructure; always on | 9 GB |
| `TTL-MAL` | `deploy/ludus/ranges/TTL-MAL.yml` | Malware and app analysis | 27 GB |
| `TTL-WKS` | `deploy/ludus/ranges/TTL-WKS.yml` | Basic AD, workstation attacks | 27 GB |
| `TTL-AD` | `deploy/ludus/ranges/TTL-AD.yml` | Full GOAD | 29 GB |

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
`10.S.20.2` using `router.iptables_commands`, the one approved use of that
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
TTL_SIEM_ES=https://10.S.20.2:9200
TTL_MAL_ENROLLMENT_TOKEN=...
TTL_WKS_ENROLLMENT_TOKEN=...
TTL_AD_ENROLLMENT_TOKEN=...
```

Before TTL-SIEM's first deploy, generate the password without printing
it, for example
`umask 077; printf 'TTL_SIEM_ELASTIC_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> ~/.config/ttl/siem.env`.

### After deploying TTL-SIEM

The `ludus_elastic_container` role registers Fleet and the Elasticsearch
output at `10.S.20.2`, and agents switch to those URLs after enrolling.
Other ranges cannot route there, so add the WAN addresses in Kibana
(Fleet API from ttl-agents):

1. Add a Fleet Server host `ttl-siem-wan`: `https://192.0.2.(100+S):8220`.
2. Add an Elasticsearch output `ttl-siem-wan`:
   `https://192.0.2.(100+S):9200`, with `ssl.verification_mode: none` in
   its advanced YAML (the certificates are self-signed for `10.S.20.2`).
3. Copy the role's `Ludus-Agent-Policy` (it already has Elastic Defend in
   detect mode and the Windows integration) once per test range:
   `TTL-MAL`, `TTL-WKS`, `TTL-AD`, with namespaces `ttl_mal`, `ttl_wks`,
   `ttl_ad`. Set each copy's Fleet Server host and output to
   `ttl-siem-wan`.
4. Create an enrollment token for each copy and add it to `siem.env`. Add
   `TTL_SIEM_WAN` and `TTL_SIEM_ES` too.
5. The owner sets `siem_wan` in the host guard to `192.0.2.(100+S)` and
   reloads it (see `deploy/ludus/host-guard/`).

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
  - `TTL-MAL`: `win11-22h2-x64-enterprise-template`, `flare-vm-template`,
    `remnux-template`, `debian-12-x64-server-template`
  - `TTL-WKS`: `win2022-server-x64-template`, `win11-22h2-x64-enterprise-template`,
    `ubuntu-22.04-x64-server-template`, `kali-x64-desktop-template`
  - `TTL-AD`: `win2019-server-x64-template`, `win2016-server-x64-template`,
    `kali-x64-desktop-template`

After that, agents create the range (`POST /ranges/create`), upload the
config, and deploy through the broker. TTL-SIEM comes first.

Elastic Defend runs in **detect** mode, not prevent. The Elastic role sets
this; check it in Kibana > Fleet after changing any policy.

## TTL-MAL: malware and app analysis

| VM | VLAN.IP | Role |
|---|---|---|
| victim | 10.21 | Windows 11 with Defend. Samples run here |
| flare | 10.22 | FLARE-VM for static and dynamic analysis |
| remnux | 10.10 | Gateway and DNS for the victim and flare. INetSim and packet capture |

Elastic Agent on the victim reports to TTL-SIEM. Packet capture runs on
remnux, not on the victim, so samples cannot see or tamper with it.

### After deploy (internet still on)

1. remnux: built from `remnux-template`, so REMnux and SSH are already
   installed. Configure INetSim to listen on remnux's VLAN 10
   address, and redirect all inbound TCP/UDP on that interface to INetSim
   with iptables, so traffic to hard-coded IPs is answered too.
2. victim and flare: set the default gateway and DNS to remnux
   (`10.X.10.10`). Add a persistent route to TTL-SIEM, `192.0.2.(100+S)/32`,
   via the router (`10.X.10.254`) so Elastic Agent still reaches Elastic.
3. flare: add a Windows Firewall rule blocking all inbound traffic from the
   victim's IP. Flare and the victim share VLAN 10, and a sample with admin
   on the victim could undo a rule placed there, so the rule lives on flare.
   Connections flare starts to the victim still work.
4. Check in Fleet that the victim is healthy under the `TTL-MAL` policy.

### Each analysis session

1. Enter testing mode. This snapshots the victim and flare and blocks
   internet for the range.
2. Check the boundary from the victim: DNS for any name resolves to
   remnux, external IPs reach only INetSim, nothing reaches the internet,
   and TTL-SIEM still receives events. Stop if any check fails.
3. Copy the sample or installer to the victim from ttl-agents.
4. Start `tcpdump` on remnux, writing one PCAP per run.
5. Run the sample. Collect the PCAP, INetSim logs, Elastic alerts and events
   (ES|QL, namespace `ttl_mal`), and notes into the run folder.
6. Leave testing mode. The victim and flare revert to their snapshots;
   remnux keeps its data, and the events stay in TTL-SIEM.

### Contained and observe modes (designed, not built)

remnux will switch the detonation network between two modes with
`ttl-mode contained|observe|status`. Neither mode can reach the home
network; the isolation layers above still apply.

- **Contained** (default; remnux boots in this mode): the victim and flare
  get only INetSim. Nothing leaves the range.
- **Observe**: victim and flare traffic leaves only through a WireGuard
  tunnel on remnux to a commercial VPN, with DNS through the tunnel. If the
  tunnel is down, nothing leaves (kill switch). The VPN account is used
  only by the lab and is not linked to the owner's personal accounts. The
  owner installs the WireGuard config on remnux; it is a secret and is
  never committed or printed. Strip any naming comment from it.

Testing mode stays on in both modes, so snapshots and reverts keep working.
In observe mode, `POST /testing/allow` permits only the VPN endpoint IP.

**Who may use observe mode:** agents may use it for app vetting. A malware
run goes into observe mode only when the owner approves that run.

`ttl-mode status` checks the actual result and writes it to the run
folder: traffic exits from the VPN's IP, contained mode answers outside
traffic with INetSim, and the home network and Ludus host are unreachable.
Each run records its mode.

**Traffic capture:** remnux captures every run's packets before the
tunnel, so the sample cannot see or tamper with the capture. By default a
run records destinations only (PCAP, DNS, TLS SNI, plus Elastic Defend's
per-process network events). To read TLS contents, pull session keys from
the victim and decrypt the remnux PCAP afterwards. This needs no CA on the
victim and works against certificate pinning:

- `SSLKEYLOGFILE`, set system-wide on the victim, covers browsers and
  OpenSSL/NSS/BoringSSL apps. It is cheap and suits app vetting.
- Schannel (WinHTTP/WinINet, most Windows-native malware) ignores it.
  Those keys need a hooking tool such as friTap. Samples can detect
  hooking, so enable it per run when needed.

mitmproxy is not used for now.

**Observe-mode hygiene:** the VPN hides the range's IP, but the VMs can
still identify their owner. Before an observe run, check that the victim
uses generic hostnames and usernames, a neutral time zone and locale, no
Microsoft account or Windows sign-in tied to a person, and no personal
logins in browsers or apps under test.

## TTL-WKS: basic AD

`ttl.lab` with DC01 (Server 2022), WS01 and WS02 (Windows 11), and an
Ubuntu server, all running Defend, with kali on VLAN 99. A GPO disables
Microsoft Defender so attack tools run. The Linux server is not joined to the
domain. Add SSSD/realmd as a setup step if a test needs it.

## TTL-AD: full GOAD

The five GOAD VMs use the names, templates and IPs from GOAD's Ludus
provider config. Deploy the VMs through the broker, then run GOAD's Ansible
playbooks from kali with a static inventory of the range IPs. Do not run
`goad.sh -p ludus`: it calls the Ludus API with its own key, which the lab
boundary forbids. The GOAD playbooks rename hosts and build the domains
after Elastic Agent is installed. Check in Fleet that every host
reports under its GOAD name.
