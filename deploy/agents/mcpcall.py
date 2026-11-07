"""Call the broker's ludus_request tool without an MCP client.

    python3 mcpcall.py '{"method": "GET", "path": "/range", "query": {"rangeID": "TTL-MAL"}}'

Other scripts can import it and use call(arguments).

Reads TTL_BROKER_URL (the broker's MCP endpoint, http://<broker>:8765/mcp)
and TTL_BROKER_TOKEN from ~/.config/ttl/broker.env, or from the environment.
Standard library only.
"""

import json
import os
import sys
import urllib.request

ENV = os.path.expanduser("~/.config/ttl/broker.env")


def setting(name):
    """Read a setting from the environment, then from ~/.config/ttl/broker.env."""
    if os.environ.get(name):
        return os.environ[name]
    for line in open(ENV):
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit(f"{name} not found in {ENV}")


def call(arguments):
    """Call ludus_request with a dict of arguments. Returns (text, is_error)."""
    url, tok, sid = setting("TTL_BROKER_URL"), setting("TTL_BROKER_TOKEN"), None

    def post(msg):
        nonlocal sid
        headers = {
            "Authorization": "Bearer " + tok,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if sid:
            headers["mcp-session-id"] = sid
        req = urllib.request.Request(url, json.dumps(msg).encode(), headers)
        with urllib.request.urlopen(req, timeout=180) as r:
            sid = r.headers.get("mcp-session-id") or sid
            body = r.read().decode()
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:])
        return json.loads(body) if body.strip() else None

    post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "mcpcall", "version": "0"}}})
    post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    res = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "ludus_request", "arguments": arguments}})
    result = res.get("result", res)
    text = "\n".join(item.get("text", "") for item in result.get("content", []))
    return text, bool(result.get("isError"))


def main():
    text, is_error = call(json.loads(sys.argv[1]))
    print(text)
    if is_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
