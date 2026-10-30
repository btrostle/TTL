What happened:
1. 20:35–20:41: the threattrails-service Ludus token cloned and started the ThreatTrails-MVP range VMs: 1004 (2 GB), 1007 Splunk (16 GB), and 1008, 1009 and 1010 (8 GB each). That's 42 GB of RAM, all with balloon 0, so none of it can be reclaimed.
2. Already running: dev-ubuntu (16 GB), threattrails-dev (8 GB), ttl-agents (8 GB), homeassistant, vlan99-gw, torrent-box and the containers. Altogether that's roughly 100 GB committed on a host with 60 GB of RAM, and it was already swapping by 20:35.
3. 21:00: the nightly vzdump backup started on top of that. Containers 101, 105 and 110 (jellyfin) finished. VM 201's backup started at 21:01:16, wrote 35 MB, and stopped at 21:04. The journal had already stopped writing at 21:00:23. At that point the host was swapping so heavily it couldn't log anything.
4. About 21:08: the guests stopped responding. tailscale-router went with them, and with it this machine's LAN route. That's why everything looked down from here.

So the other Claude session did contribute, indirectly. Its firewall rules didn't break anything. The Ludus range it deployed is what used up the RAM, and the 21:00 backup collided with it.

Two settings that made it worse:
- Swappiness isn't what you set. /etc/sysctl.conf sets vm.swappiness=0, but the live value is 60. That file seems to not be getting applied; putting the setting in /etc/sysctl.d/ works.
- KSM is off. KSM is the kernel feature that merges duplicate memory pages between VMs, and it can save a lot when several clones run from the same templates.

Fixes, starting with the biggest win:
1. Don't run the full ThreatTrails range alongside everything else. Either cut its RAM (Splunk at 16 GB is the big one), or enable ballooning so idle VMs give memory back.
2. Keep backups away from the range. Move the backup time, or stop the range VMs before 21:00.
3. Move vm.swappiness into /etc/sysctl.d/99-swappiness.conf, and consider enabling ksmtuned.
4. Delete the half-finished 201 backup: /mnt/hdd/backups/dump/vzdump-qemu-201-2026_10_28-21_01_16.{tmp,vma.dat}.
5. Revoke the UDM API key, since it's in this transcript.
