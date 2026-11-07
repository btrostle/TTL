"""Check or fix the clocks of a range's Windows VMs, from ttl-agents' clock.

    python3 ~/ttl/timesync.py TTL-MAL            # fix every Windows VM more than 2 s off
    python3 ~/ttl/timesync.py TTL-MAL --check    # only report each VM's offset
    python3 ~/ttl/timesync.py TTL-MAL dynamic    # only VMs whose name contains "dynamic"

Windows VMs often boot hours off (Proxmox hands them host-local time and they
may not sync over NTP for hours), and VMs without internet, such as TTL-MAL's
dynamic VM in testing mode, can't sync at all. This sets them from ttl-agents,
which syncs over NTP, through WinRM. It needs no internet on the VM. Hosts,
users and passwords come from the range's Ansible inventory (range VM
passwords aren't secrets). Needs python3-winrm and python3-yaml.
"""

import json
import os
import sys
import time

import winrm
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpcall import call  # noqa: E402

TOLERANCE = 2.0  # seconds; a WinRM round trip makes the measurement about 1 s rough
READ_UTC = "[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()"


def windows_hosts(range_id):
    out, err = call({"method": "GET", "path": "/range/ansibleinventory", "query": {"rangeID": range_id}})
    body = json.loads(out)["body"]
    try:
        body = json.loads(body)["result"]
    except (TypeError, ValueError, KeyError):
        pass
    # Ansible prints warnings before the YAML.
    inventory = yaml.safe_load(body[body.index("all:"):])
    hosts = {}

    def walk(group):
        for name, hostvars in ((group or {}).get("hosts") or {}).items():
            if (hostvars or {}).get("ansible_connection") == "winrm":
                hosts[name] = hostvars
        for child in ((group or {}).get("children") or {}).values():
            walk(child)

    walk(inventory["all"])
    return hosts


def session(v):
    scheme = v.get("ansible_winrm_scheme", "https")
    port = v.get("ansible_port", 5986 if scheme == "https" else 5985)
    return winrm.Session(f"{scheme}://{v['ansible_host']}:{port}/wsman",
                         auth=(v["ansible_user"], v["ansible_password"]),
                         transport="ntlm", server_cert_validation="ignore",
                         operation_timeout_sec=20, read_timeout_sec=30)


def offset(s):
    """Seconds the VM is ahead of ttl-agents (negative: behind)."""
    t0 = time.time()
    r = s.run_ps(READ_UTC)
    t1 = time.time()
    if r.status_code != 0:
        raise RuntimeError(r.std_err.decode(errors="replace")[:200])
    return int(r.std_out.decode().strip()) / 1000 - (t0 + t1) / 2


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not 1 <= len(args) <= 2:
        sys.exit(__doc__)
    check_only = "--check" in sys.argv
    hosts = windows_hosts(args[0])
    if len(args) == 2:
        hosts = {n: v for n, v in hosts.items() if args[1] in n}
    if not hosts:
        sys.exit("No Windows VMs found.")

    failed = False
    for name, v in sorted(hosts.items()):
        try:
            s = session(v)
            s.run_ps("$null")  # log in first, so the login isn't timed
            off = offset(s)
            if check_only or abs(off) <= TOLERANCE:
                print(f"{name}: {off:+.1f} s{'' if abs(off) <= TOLERANCE else '  OFF'}")
                failed |= abs(off) > TOLERANCE
                continue
            # Relative adjustment, so the WinRM delay doesn't matter.
            r = s.run_ps(f"Set-Date -Adjust ([TimeSpan]::FromMilliseconds({-off * 1000:.0f})) | Out-Null")
            if r.status_code != 0:
                raise RuntimeError(r.std_err.decode(errors="replace")[:200])
            after = offset(s)
            print(f"{name}: was {off:+.1f} s, now {after:+.1f} s")
            failed |= abs(after) > TOLERANCE
        except Exception as e:  # report and carry on with the other VMs
            print(f"{name}: unreachable or failed: {e}")
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
