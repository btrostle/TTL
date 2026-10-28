# TTL

ThreatTrails Lab. Agents run techniques in a Ludus lab and return
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

An agent runs one technique on one lab host and produces a run folder with the
commands, outputs, and Splunk events.

## Deployed broker

The broker runs on `threattrails-dev.home:8765` as the systemd service
`ttl-broker`, installed with `sudo sh deploy/install.sh` from a copy of this
repo. It reads the Ludus key through systemd `LoadCredential` from
`/etc/threattrails/secrets/ludus_api_key` and checks the Ludus certificate
(Proxmox's, issued to `ludus`) against `/opt/ttl-broker/ludus.pem`. Its settings and bearer token are in
`/etc/ttl-broker/env` (root only): `sudo sed -n 's/^BROKER_TOKEN=//p'
/etc/ttl-broker/env`.
