"""Fill a range config's secret placeholders and upload it, without printing them.

    python3 ~/ttl/upload-config.py TTL-MAL           # upload ~/ttl/ranges/TTL-MAL.yml
    python3 ~/ttl/upload-config.py TTL-MAL --check   # only list placeholders and whether each is set

Range configs in the repo hold placeholders such as TTL_SIEM_WAN,
TTL_SIEM_ELASTIC_PASSWORD and TTL_MAL_ENROLLMENT_TOKEN. Their values live in
~/.config/ttl/siem.env (NAME=value lines, mode 600). This script replaces every
placeholder, uploads the result with PUT /range/config, reads the live config
back and reports only whether it matches. It never prints the values.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpcall import call  # noqa: E402

ENV = os.path.expanduser("~/.config/ttl/siem.env")
RANGES = os.path.expanduser("~/ttl/ranges")
PLACEHOLDER = re.compile(r"\bTTL_[A-Z0-9_]+\b")


def read_env(path):
    values = {}
    if not os.path.exists(path):
        return values
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"')
    return values


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    range_id = args[0]
    text = open(os.path.join(RANGES, range_id + ".yml")).read()
    env = read_env(ENV)
    names = sorted(set(PLACEHOLDER.findall(text)))
    missing = [n for n in names if not env.get(n)]

    if "--check" in sys.argv:
        for n in names:
            print(f"{n}: {'set' if env.get(n) else 'MISSING'}")
        sys.exit(1 if missing else 0)
    if missing:
        sys.exit(f"Not set in {ENV}: {', '.join(missing)}. Nothing uploaded.")

    for n in names:
        text = re.sub(r"\b" + n + r"\b", lambda _m, v=env[n]: v, text)

    out, err = call({"method": "PUT", "path": "/range/config", "query": {"rangeID": range_id},
                     "body": {"force": "false"}, "file_text": text})
    if err:
        # Ludus echoes errors, not the config, but scrub values anyway.
        for n in names:
            out = out.replace(env[n], n)
        sys.exit("Upload failed: " + out)

    live, err = call({"method": "GET", "path": "/range/config", "query": {"rangeID": range_id}})
    try:
        data = json.loads(live)
        live = data.get("result", live) if isinstance(data, dict) else live
    except ValueError:
        pass
    same = isinstance(live, str) and live.strip() == text.strip()
    print(f"Uploaded {range_id} ({len(names)} placeholders filled). "
          f"Live config {'matches' if same else 'DIFFERS from'} the filled file.")
    if not same:
        sys.exit(1)


if __name__ == "__main__":
    main()
