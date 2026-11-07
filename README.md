# TTL

ThreatTrails Lab. Agents run security tests in a Ludus lab and return
the commands, outputs, and telemetry.

The previous project is archived at
[btrostle/threattrails-lab](https://github.com/btrostle/threattrails-lab), tag
`archive/threattrails-v1`.

## Ludus broker

`ttl-broker` is an MCP server that gives agents the Ludus API without the
Ludus key. It allows range work (status, config, deploy, power, snapshots,
testing mode, templates, Ansible, blueprints) on an allowlist of ranges, and
blocks operations that return Ludus or Proxmox credentials, Ludus
administration, and Proxmox host changes. The full list is in
`src/ttl_broker/policy.py`.

Run it on its own box, not the agent's, so the agent cannot read the key:

```sh
export LUDUS_URL=https://198.51.100.1:8080
export LUDUS_API_KEY_FILE=/path/to/key # only this process reads it
export LUDUS_ALLOWED_RANGES=TTL-1,TTL-2
export LUDUS_CA_FILE=/path/to/ludus.pem       # or LUDUS_INSECURE_TLS=1
export LUDUS_TLS_SERVER_NAME=ludus        # name on the Ludus certificate
export BROKER_TOKEN=...             # agents send this as a bearer token
uv run ttl-broker                   # listens on 0.0.0.0:8765, path /mcp
```

Point the agent at `http://<broker-host>:8765/mcp` with the header
`Authorization: Bearer <BROKER_TOKEN>`. The agent's own VPN peer must not
reach the Ludus host, or the agent can go around the broker.

Run the tests with `uv run pytest`.

## First milestone

An agent runs one test on one lab host and produces a run folder with the
commands, outputs, and Elastic events.

## Deploy the broker with Docker

On the broker host (`threattrails-dev.home`), from a clone of this repo. The
host needs Docker and a route to Ludus (its WireGuard tunnel); the container
uses the host's routing.

```sh
mkdir -p secrets
# The Ludus key, readable only by the container's user (uid 10001).
sudo install -m 400 -o 10001 /path/to/ludus_api_key secrets/ludus_api_key
# Pin the certificate Ludus presents now (Proxmox's, issued to "ludus").
echo | openssl s_client -connect 198.51.100.1:8080 2>/dev/null | openssl x509 > secrets/ludus.pem
cp deploy/broker/broker.env.example broker.env   # set LUDUS_URL, ranges, BROKER_TOKEN
docker compose up -d --build
```

Update with `git pull && docker compose up -d --build`. Logs:
`docker compose logs -f`. The container runs read-only, as a non-root user,
with no capabilities.

### Without Docker

`sudo sh deploy/broker/install.sh` installs the systemd service `ttl-broker`. It
reads the Ludus key through systemd `LoadCredential` from
`/etc/threattrails/secrets/ludus_api_key`, pins the certificate to
`/opt/ttl-broker/ludus.pem`, and keeps its settings and bearer token in
`/etc/ttl-broker/env` (root only): `sudo sed -n 's/^BROKER_TOKEN=//p'
/etc/ttl-broker/env`.

## Agents box

`ttl-agents` (Ubuntu 24.04, Dev VLAN) runs the agent harnesses (herdr, Claude
Code, Codex) as the unprivileged user `agent`. `deploy/agents/agents-box.sh` sets it
up from a fresh VM: a root-only WireGuard tunnel for the agents' own Ludus
user, routing only the range subnets; no sudo for `agent`; and an nftables
backstop that rejects `agent` traffic to the Ludus host. Agents reach Ludus
only through the broker. `/home/agent/.config/ttl/broker.env` holds
`TTL_BROKER_URL` (the broker's MCP endpoint, `http://<broker>:8765/mcp`) and
`TTL_BROKER_TOKEN`.
