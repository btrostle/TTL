# To do

- Broker container for people sharing this project (not for our own deploy,
  which stays on systemd). Drafted but never built: `Dockerfile`,
  `compose.yaml`, `deploy/broker/broker.env.example`, `.dockerignore`, and the README's
  Docker section. Left to do:
  - Build and run it once on a host that can reach Ludus; check that an agent
    can call `list_operations` through it.
  - Pin the uv image to an exact version (`ghcr.io/astral-sh/uv:0.12` is a
    guess from `uv_build>=0.12.21`).
  - Make the README generic: any host with a route to Ludus, not
    `threattrails-dev`, and never a host where agents run (Docker group access
    is root-equivalent and would expose the Ludus key).
  - Compose secrets keep host permissions: the key file must be readable by
    uid 10001.
- Benign background activity in ranges:
  - GHOSTS (CMU SEI): simulated-user agents on the workstation and GOAD
    ranges so Elastic collects real benign telemetry. Check the server's RAM
    against the 45 GB range cap.
  - BadBlood: fill AD with realistic users, groups, OUs, and ACLs on the AD
    ranges.
