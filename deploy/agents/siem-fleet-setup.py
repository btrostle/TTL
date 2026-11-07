"""Set up TTL-SIEM's Fleet for the test ranges. Safe to re-run.

    python3 ~/ttl/siem-fleet-setup.py

Run after TTL-SIEM is (re)deployed. Reads TTL_SIEM_ES, TTL_SIEM_WAN and
TTL_SIEM_ELASTIC_PASSWORD from ~/.config/ttl/siem.env, then:

1. points Fleet at TTL-SIEM's WAN address, which test ranges reach
   through its router: adds Fleet Server host `ttl-siem-wan`
   (https://TTL_SIEM_WAN:8220) as the default, and changes the default
   output, which the role preconfigures in /opt/elastic_container/kibana.yml
   on the Elastic VM, to https://TTL_SIEM_WAN:9200 (over SSH, then restarts
   Kibana). Basic has no per-policy outputs, so Elastic's own agent uses the
   WAN address too, through the router's hairpin rules;
2. copies Ludus-Agent-Policy once per test range (TTL-MAL, TTL-WKS, TTL-AD)
   with that range's namespace, on its integrations too;
3. writes each policy's enrollment token to siem.env as
   TTL_<RANGE>_ENROLLMENT_TOKEN.

It never prints the password or the tokens.
"""

import base64
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ENV = os.path.expanduser("~/.config/ttl/siem.env")
SOURCE_POLICY = "Ludus-Agent-Policy"
RANGES = {"TTL-MAL": "ttl_mal", "TTL-WKS": "ttl_wks", "TTL-AD": "ttl_ad"}
WAN_ID = "ttl-siem-wan"
KIBANA_YML = "/opt/elastic_container/kibana.yml"
# Range VM passwords are lab credentials, not secrets (Ludus default: debian).
VM_PASSWORD = os.environ.get("TTL_SIEM_VM_PASSWORD", "debian")


def vm_sudo(host, script):
    """Run a shell script as root on a TTL-SIEM VM with password SSH."""
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(f"#!/bin/sh\necho '{VM_PASSWORD}'\n")
    os.chmod(f.name, 0o700)
    try:
        env = dict(os.environ, SSH_ASKPASS=f.name, SSH_ASKPASS_REQUIRE="force")
        # sudo -S takes the password from the first line of stdin, sh the rest.
        r = subprocess.run(["setsid", "ssh", "-o", "StrictHostKeyChecking=accept-new",
                            "-o", "PubkeyAuthentication=no", "-o", "IdentityAgent=none",
                            f"debian@{host}", "sudo -S -p '' sh -s"],
                           env=env, input=VM_PASSWORD + "\n" + script,
                           capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    if r.returncode:
        sys.exit(f"ssh {host} failed: {r.stderr.strip()[-500:]}")
    return r.stdout


def defend_modes(pkg):
    """Elastic Defend's protection modes per OS, e.g. {"windows": {"malware": "detect", ...}}."""
    policy = pkg["inputs"][0]["config"]["policy"]["value"]
    return {os_name: {k: v["mode"] for k, v in conf.items()
                      if isinstance(v, dict) and "mode" in v}
            for os_name, conf in policy.items() if isinstance(conf, dict)}


def read_env():
    values = {}
    for line in open(ENV):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"')
    return values


def set_env(name, value):
    text = open(ENV).read()
    line = f"{name}={value}"
    if re.search(rf"^{name}=", text, flags=re.M):
        text = re.sub(rf"^{name}=.*$", lambda _m: line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    old = os.umask(0o077)
    try:
        with open(ENV + ".new", "w") as f:
            f.write(text)
    finally:
        os.umask(old)
    os.replace(ENV + ".new", ENV)


class Kibana:
    def __init__(self, base, password):
        self.base = base
        self.auth = base64.b64encode(f"elastic:{password}".encode()).decode()
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname, self.ctx.verify_mode = False, ssl.CERT_NONE

    def __call__(self, method, path, body=None, ok404=False):
        req = urllib.request.Request(
            self.base + path, json.dumps(body).encode() if body is not None else None,
            {"Authorization": "Basic " + self.auth, "Content-Type": "application/json",
             "kbn-xsrf": "ttl"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120, context=self.ctx) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if ok404 and e.code == 404:
                return None
            sys.exit(f"{method} {path}: HTTP {e.code}: {e.read().decode()[:1000]}")


def main():
    env = read_env()
    try:
        es, wan, password = env["TTL_SIEM_ES"], env["TTL_SIEM_WAN"], env["TTL_SIEM_ELASTIC_PASSWORD"]
    except KeyError as e:
        sys.exit(f"{e.args[0]} not set in {ENV}")
    host = urllib.parse.urlsplit(es).hostname
    kb = Kibana(f"https://{host}:5601", password)

    # 1. Fleet Server host and output on TTL-SIEM's WAN address.
    fleet = {"name": WAN_ID, "host_urls": [f"https://{wan}:8220"], "is_default": True}
    if kb("GET", f"/api/fleet/fleet_server_hosts/{WAN_ID}", ok404=True):
        kb("PUT", f"/api/fleet/fleet_server_hosts/{WAN_ID}", fleet)
    else:
        kb("POST", "/api/fleet/fleet_server_hosts", {"id": WAN_ID, **fleet})
    wan_es = f"https://{wan}:9200"
    if kb("GET", "/api/fleet/outputs/fleet-default-output")["item"]["hosts"] != [wan_es]:
        vm_sudo(host, f"""set -e
sed -i 's#^\\( *hosts: \\)\\["https://[^"]*:9200"\\]#\\1["{wan_es}"]#' {KIBANA_YML}
grep -q '"{wan_es}"' {KIBANA_YML}
docker restart ecp-kibana >/dev/null
""")
        for _ in range(60):
            time.sleep(10)
            try:
                if kb("GET", "/api/fleet/outputs/fleet-default-output")["item"]["hosts"] == [wan_es]:
                    break
            except (SystemExit, OSError):  # Kibana still starting
                pass
        else:
            sys.exit(f"Default output still not {wan_es} after restarting Kibana")
    print(f"Default Fleet host {WAN_ID} https://{wan}:8220, default output {wan_es}")

    # 2. One policy per test range.
    policies = {p["name"]: p for p in
                kb("GET", "/api/fleet/agent_policies?perPage=100")["items"]}
    if SOURCE_POLICY not in policies:
        sys.exit(f"{SOURCE_POLICY} not found; is TTL-SIEM fully deployed?")
    kuery = urllib.parse.quote(f'ingest-package-policies.policy_ids:"{policies[SOURCE_POLICY]['id']}"')
    source_defend = [defend_modes(p) for p in
                     kb("GET", f"/api/fleet/package_policies?perPage=100&kuery={kuery}")["items"]
                     if p["package"]["name"] == "endpoint"]
    if len(source_defend) != 1:
        sys.exit(f"{SOURCE_POLICY} has {len(source_defend)} Elastic Defend integrations, expected 1")
    source_defend = source_defend[0]
    for name, namespace in RANGES.items():
        policy = policies.get(name)
        if not policy:
            policy = kb("POST", f"/api/fleet/agent_policies/{policies[SOURCE_POLICY]['id']}/copy",
                        {"name": name, "description": f"{name} agents; copied from {SOURCE_POLICY}"})["item"]
        pid = policy["id"]
        kb("PUT", f"/api/fleet/agent_policies/{pid}", {"name": name, "namespace": namespace})
        kuery = urllib.parse.quote(f'ingest-package-policies.policy_ids:"{pid}"')
        for pkg in kb("GET", f"/api/fleet/package_policies?perPage=100&kuery={kuery}")["items"]:
            if pkg.get("namespace") != namespace:
                kb("PUT", f"/api/fleet/package_policies/{pkg['id']}", {"namespace": namespace})
        pkgs = kb("GET", f"/api/fleet/package_policies?perPage=100&kuery={kuery}")["items"]
        wrong = [p["name"] for p in pkgs if p.get("namespace") != namespace]
        if wrong:
            sys.exit(f"{name}: integrations still outside {namespace}: {wrong}")
        # Defend settings must match the source policy (detect, not prevent or off).
        copy = [defend_modes(p) for p in pkgs if p["package"]["name"] == "endpoint"]
        if copy != [source_defend]:
            sys.exit(f"{name}: Elastic Defend {copy} differs from {SOURCE_POLICY} "
                     f"{source_defend}. If no agents are enrolled, delete the policy and re-run.")

        # 3. Enrollment token.
        kuery = urllib.parse.quote(f'policy_id:"{pid}"')
        keys = [k for k in kb("GET", f"/api/fleet/enrollment_api_keys?perPage=100&kuery={kuery}")["items"]
                if k.get("active")]
        if not keys:
            keys = [kb("POST", "/api/fleet/enrollment_api_keys", {"policy_id": pid})["item"]]
        token_name = "TTL_" + name.split("-", 1)[1] + "_ENROLLMENT_TOKEN"
        set_env(token_name, keys[0]["api_key"])
        print(f"{name}: policy {pid}, namespace {namespace} ({len(pkgs)} integrations), "
              f"{token_name} written to siem.env")


if __name__ == "__main__":
    main()
