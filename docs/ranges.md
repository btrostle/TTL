# Ranges

Three ranges, each built for one kind of attack telemetry. Only one runs at a
time, and each must stay under the 45 GB RAM soft cap. All of them send
telemetry to Elastic (Elastic Defend in detect mode, Basic license, prebuilt
SIEM rules) rather than Splunk.

| Range | Config | Purpose | RAM |
|---|---|---|---|
| `TTL-MAL` | `deploy/ranges/TTL-MAL.yml` | Malware and app analysis | 35 GB |
| `TTL-WKS` | `deploy/ranges/TTL-WKS.yml` | Basic AD, workstation attacks | 35 GB |
| `TTL-AD` | `deploy/ranges/TTL-AD.yml` | Full GOAD | 37 GB |

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
   `deploy/ludus-host-guard/`, which has the rules, install steps and the
   check.

Verify layer 2 from a range router (see `deploy/ludus-host-guard/`): home
addresses, the Proxmox UI and the Ludus API must be unreachable, and the
internet reachable. Templates that use Packer's HTTP server must be built
through `ttl-template-window.sh`.

## Owner setup (all ranges)

- Add the range IDs to `LUDUS_ALLOWED_RANGES` on the broker.
- Install `badsectorlabs.ludus_elastic_container` and
  `badsectorlabs.ludus_elastic_agent` globally as the Ludus admin.
- Build any missing templates. Check them with `GET /templates`.
  - `TTL-MAL`: `win11-22h2-x64-enterprise-template`, `flare-vm-template`,
    `ubuntu-24.04-x64-server-template`, `debian-12-x64-server-template`
  - `TTL-WKS`: `win2022-server-x64-template`, `win11-22h2-x64-enterprise-template`,
    `ubuntu-22.04-x64-server-template`, `kali-x64-desktop-template`
  - `TTL-AD`: `win2019-server-x64-template`, `win2016-server-x64-template`,
    `kali-x64-desktop-template`

After that, agents create the range (`POST /ranges/create`), upload the
config, and deploy through the broker.

After every deploy, open Kibana > Fleet > the agent policy > Elastic
Defend, and set each protection to **detect**, not prevent.

## TTL-MAL: malware and app analysis

| VM | VLAN.IP | Role |
|---|---|---|
| victim | 10.21 | Windows 11 with Defend. Samples run here |
| flare | 10.22 | FLARE-VM for static and dynamic analysis |
| remnux | 10.10 | Gateway and DNS for the victim and flare. INetSim and packet capture |
| elastic | 20.2 | Elasticsearch, Kibana, Fleet |

VLAN 10 can reach only the Elastic ports (5601, 8220, 9200) on VLAN 20.
Packet capture runs on remnux, not on the victim, so samples cannot see or
tamper with it.

### After deploy (internet still on)

1. remnux: install REMnux with `sudo remnux install --mode=cloud`. Cloud mode
   keeps SSH enabled. Configure INetSim to listen on remnux's VLAN 10
   address, and redirect all inbound TCP/UDP on that interface to INetSim
   with iptables, so traffic to hard-coded IPs is answered too.
2. victim and flare: set the default gateway and DNS to remnux
   (`10.X.10.10`). Add a persistent route `10.X.20.0/24` via the router
   (`10.X.10.254`) so Elastic Agent still reaches Elastic.
3. Set Defend to detect (see above).

### Each analysis session

1. Enter testing mode. This snapshots the victim and flare and blocks
   internet for the range.
2. Check the boundary from the victim: DNS for any name resolves to
   remnux, external IPs reach only INetSim, nothing reaches the internet,
   and Elastic still receives events. Stop if any check fails.
3. Copy the sample or installer to the victim from ttl-agents.
4. Start `tcpdump` on remnux, writing one PCAP per run.
5. Run the sample. Collect the PCAP, INetSim logs, Elastic alerts and events
   (ES|QL), and notes into the run folder.
6. Leave testing mode. The victim and flare revert to their snapshots;
   remnux and Elastic keep their data.

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
