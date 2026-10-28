# TTL

ThreatTrails Lab, restarted. Agents run techniques in a Ludus lab and return
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
export LUDUS_API_KEY=...            # only this process holds it
export LUDUS_ALLOWED_RANGES=TTL-1,TTL-2
export LUDUS_CA_FILE=/path/to/ludus-ca.pem   # or LUDUS_INSECURE_TLS=1
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
