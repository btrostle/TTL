# Common Ludus errors

Each entry says who can fix it:

- **Agent**: through the broker or on the range VMs.
- **Owner**: needs a root shell on the Ludus or Proxmox host, the Proxmox UI,
  or a Ludus admin. Report the symptom, the evidence, and the doc link. Do not
  try to do it yourself.

## Table of Contents

- [Ansible and deploy](#ansible-and-deploy)
- [Templates](#templates)
- [Network](#network)
- [WireGuard](#wireguard)
- [Proxmox](#proxmox)
- [Other](#other)

## Ansible and deploy

### "Failed to create temporary directory" (Agent)

`UNREACHABLE! => {"changed": false, "msg": "Failed to create temporary
directory...", "unreachable": true}`. The key sign is `"unreachable": true`.

Fix: check the VM is powered on (`GET /range`) and answers on SSH or WinRM.
Power it on with `PUT /range/poweron` (ask the owner first), then rerun the
deploy limited to that VM.

### Deploy fails once, then works (Agent)

Ludus actions are idempotent. Complex VMs sometimes need a second deploy.
Rerun before you dig further, unless the same task fails the same way twice.

### Targeted reruns (Agent)

Send these in the `POST /range/deploy` body:

- `"tags": "network"`: network and firewall rules.
- `"tags": "user-defined-roles"`: only the Ansible roles.
- `"tags": "custom-groups"`: Ansible groups.
- `"tags": "share"`: SMB shares.
- `"only_roles": ["<role>"]`: one role.
- `"limit": "ThreatTrails-MVP-<vm>"`: one VM. `localhost` matches nothing.

### "Unable to retrieve API task ID from node ... port=8006: Read timed out" (Owner)

A Proxmox certificate problem on the host. Docs:
https://docs.ludus.cloud/docs/troubleshooting/client

## Templates

### Template build fails (Agent to diagnose, Owner to fix the host)

- Status: `GET /templates/status`.
- Log: `GET /templates/logs`; older runs `GET /templates/logs/history`.
- Cancel a stuck build: `POST /templates/abort`.
- Retry one template: `POST /templates` with `{"templates": ["<name>"]}`.
  Ask the owner first; builds load the host.

ISO download failures and full disks are the owner's.

### Kali APT `undefined symbol` or GRUB error during build (Owner)

Known Kali bugs. The workarounds edit packer files on the Ludus host or use
the Proxmox console. Docs:
https://docs.ludus.cloud/docs/troubleshooting/client

### Flare-VM: `ScriptContainedMaliciousContent` (Owner)

Needs the dedicated `flare-vm` template added on the Ludus host. Once it is
built, set `template: flare-vm-template` in the range config.

### Packer cache fills the disk (Owner)

ISOs pile up in the Ludus user's packer cache on the host.
https://docs.ludus.cloud/docs/troubleshooting/packer-cache-cleanup

## Network

### VMs get 169.254.x.x or cannot reach the internet (Owner)

Usually dnsmasq or the NAT bridge on the Ludus host. First check from the VM
that testing mode is off (`testingEnabled` in `GET /range`); testing mode
blocks the internet on purpose. If testing is off, report it. Docs:
https://docs.ludus.cloud/docs/troubleshooting/network/

### Range VMs unreachable after a network change (Agent)

Rerun the network stage: `POST /range/deploy` with `{"tags": "network"}`.

## WireGuard

The tunnel on `ttl-agents` is root-owned. You cannot read or change it. If
the range does not answer over the tunnel, report it to the owner. Handshake
errors, hanging TCP connections (MTU, MSS clamping), and WireGuard debugging
are all host-side. Docs:
https://docs.ludus.cloud/docs/troubleshooting/wireguard/

## Proxmox

Blank Proxmox web UI, 500 errors, and API 596 timeouts are host problems
(Owner). Agents never log in to Proxmox.

## Other

### Lost API key (Owner)

Never attempt key recovery. The broker holds the only key agents use.

### KasmVNC page has no stylesheet (Agent)

Known bug. In the browser's network tab, reload, open `style.dist.css` in a
new window, then reload the KasmVNC page.

### Bug reports

Attach the failing part of `GET /range/logs`. Remove range passwords before
you share any output.

Adapted from `troubleshooting/references/common-errors.md` in
https://gitlab.com/badsectorlabs/ludus-skills (MIT).
