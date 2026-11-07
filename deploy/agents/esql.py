"""Run an ES|QL query on TTL-SIEM's Elasticsearch.

    python3 ~/ttl/esql.py 'FROM logs-endpoint.events.process-ttl_mal | LIMIT 10'
    python3 ~/ttl/esql.py --format csv '<query>' > elastic/process.csv

Reads TTL_SIEM_ES (https://10.S.100.2:9200) and TTL_SIEM_ELASTIC_PASSWORD from
~/.config/ttl/siem.env. Prints only the results (txt by default; csv, tsv or
json with --format). The certificate is self-signed, so it is not verified.
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

ENV = os.path.expanduser("~/.config/ttl/siem.env")


def read_env(path):
    values = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"')
    return values


def main():
    args, fmt = sys.argv[1:], "txt"
    if args[:1] == ["--format"] and len(args) >= 2:
        fmt, args = args[1], args[2:]
    if len(args) != 1:
        sys.exit(__doc__)
    env = read_env(ENV)
    try:
        base, password = env["TTL_SIEM_ES"].rstrip("/"), env["TTL_SIEM_ELASTIC_PASSWORD"]
    except KeyError as e:
        sys.exit(f"{e.args[0]} not set in {ENV}")

    auth = base64.b64encode(f"elastic:{password}".encode()).decode()
    req = urllib.request.Request(
        f"{base}/_query?format={fmt}", json.dumps({"query": args[0]}).encode(),
        {"Authorization": "Basic " + auth, "Content-Type": "application/json"})
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            sys.stdout.write(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:2000]}")


if __name__ == "__main__":
    main()
