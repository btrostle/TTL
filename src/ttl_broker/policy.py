"""Which Ludus API operations agents may call, and on which ranges.

Everything not listed here is blocked. Left out on purpose: operations that
return or set Ludus or Proxmox credentials (user credentials, API key,
WireGuard config, VM console tickets, user creation), Ludus administration
(users, groups, quotas, range assignment, blueprint sharing), and Proxmox host
changes (SDN and SQLite migration, anti-sandbox and KMS installs,
diagnostics).
"""

import re
from typing import Any, Literal

RangeIn = Literal["query", "path", "body"] | None

# (method, path template, where the operation names its range)
OPERATIONS: list[tuple[str, str, RangeIn]] = [
    ("GET", "/", None),
    ("GET", "/openapi", None),
    ("GET", "/whoami", None),
    ("GET", "/user/default-range", None),
    ("GET", "/user/quotas", None),
    # Ansible
    ("GET", "/ansible", None),
    ("GET", "/ansible/subscription-roles", None),
    ("POST", "/ansible/subscription-roles", None),
    ("POST", "/ansible/role/vars", None),
    ("POST", "/ansible/collection", None),
    ("PATCH", "/ansible/role/scope", None),
    ("POST", "/ansible/role", None),
    # Ranges
    ("POST", "/ranges/create", "body"),
    ("GET", "/ranges/accessible", None),
    ("GET", "/range/all", None),
    ("GET", "/range/tags", None),
    ("GET", "/range/config/example", None),
    ("GET", "/range/sshconfig", None),
    ("GET", "/range", "query"),
    ("DELETE", "/range", "query"),
    ("POST", "/range/abort", "query"),
    ("DELETE", "/range/{rangeID}/vms", "path"),
    ("GET", "/range/config", "query"),
    ("PUT", "/range/config", "query"),
    ("POST", "/range/deploy", "query"),
    ("GET", "/range/logs", "query"),
    ("GET", "/range/logs/history", "query"),
    ("GET", "/range/logs/history/{logID}", "query"),
    ("GET", "/range/etchosts", "query"),
    ("GET", "/range/rdpconfigs", "query"),
    ("GET", "/range/ansibleinventory", "query"),
    ("GET", "/range/auto-shutdown", "query"),
    ("PUT", "/range/auto-shutdown", "query"),
    ("PUT", "/range/poweron", "query"),
    ("PUT", "/range/poweroff", "query"),
    # Testing mode
    ("PUT", "/testing/start", "query"),
    ("PUT", "/testing/stop", "query"),
    ("POST", "/testing/allow", "query"),
    ("POST", "/testing/deny", "query"),
    ("POST", "/testing/update", "query"),
    # Snapshots
    ("GET", "/snapshots/list", "query"),
    ("POST", "/snapshots/create", "query"),
    ("POST", "/snapshots/rollback", "query"),
    ("POST", "/snapshots/remove", "query"),
    # VM settings inside a range
    ("POST", "/antisandbox/enable", "query"),
    ("POST", "/kms/license", "query"),
    # Templates
    ("GET", "/templates", None),
    ("POST", "/templates", None),
    ("DELETE", "/template/{name}", None),
    ("POST", "/templates/abort", None),
    ("GET", "/templates/logs", None),
    ("GET", "/templates/status", None),
    ("GET", "/templates/logs/history", None),
    ("GET", "/templates/logs/history/{logID}", None),
    # Blueprints
    ("GET", "/blueprints", None),
    ("POST", "/blueprints", None),
    ("POST", "/blueprints/import", None),
    ("POST", "/blueprints/from-range", "body"),
    ("GET", "/blueprints/{blueprintID}", None),
    ("DELETE", "/blueprints/{blueprintID}", None),
    ("POST", "/blueprints/{blueprintID}/copy", None),
    ("POST", "/blueprints/{blueprintID}/apply", "body"),
    ("GET", "/blueprints/{blueprintID}/config", None),
    ("PUT", "/blueprints/{blueprintID}/config", None),
    ("POST", "/blueprints/{blueprintID}/install", None),
    ("GET", "/blueprints/{blueprintID}/export", None),
    # Sources
    ("GET", "/sources", None),
    ("POST", "/sources", None),
    ("GET", "/sources/{sourceID}", None),
    ("PATCH", "/sources/{sourceID}", None),
    ("DELETE", "/sources/{sourceID}", None),
    ("GET", "/sources/{sourceID}/catalog", None),
    ("POST", "/sources/{sourceID}/install", None),
    ("POST", "/sources/{sourceID}/sync", None),
    ("GET", "/sources/{sourceID}/blueprints", None),
    ("GET", "/sources/{sourceID}/templates", None),
    ("GET", "/sources/{sourceID}/roles", None),
    ("GET", "/sources/{sourceID}/collections", None),
]

_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")


class PolicyError(Exception):
    pass


def _match(path: str) -> list[tuple[str, str, RangeIn, dict[str, str]]]:
    if path == "/":
        return [(m, t, r, {}) for m, t, r in OPERATIONS if t == "/"]
    parts = path.split("/")[1:]
    matches = []
    for method, template, range_in in OPERATIONS:
        tparts = template.split("/")[1:]
        if len(tparts) != len(parts):
            continue
        params = {}
        for t, p in zip(tparts, parts):
            if t.startswith("{"):
                params[t[1:-1]] = p
            elif t != p:
                break
        else:
            matches.append((method, template, range_in, params))
    return matches


def check(
    method: str,
    path: str,
    query: dict[str, Any],
    body: dict[str, Any] | None,
    allowed_ranges: frozenset[str],
) -> None:
    """Raise PolicyError unless the call is allowed."""
    method = method.upper()
    if not path.startswith("/") or (
        path != "/" and not all(_SEGMENT.fullmatch(s) and s not in (".", "..") for s in path.split("/")[1:])
    ):
        raise PolicyError(f"malformed path {path!r}: use /segment/segment with query parameters passed separately")

    found = [(t, r, p) for m, t, r, p in _match(path) if m == method]
    if not found:
        raise PolicyError(f"{method} {path} is not allowed by the broker policy")
    _, range_in, params = found[0]

    body = body or {}
    if "userID" in query or "userID" in body:
        raise PolicyError("userID is not allowed: agents act only as the broker's own Ludus user")

    ranges = {
        "query": query.get("rangeID"),
        "path": params.get("rangeID"),
        "body": body.get("rangeID"),
    }
    if range_in is not None and not ranges[range_in]:
        raise PolicyError(f"rangeID is required in the {range_in} for {method} {path}")
    for value in ranges.values():
        if value is not None and (not isinstance(value, str) or value not in allowed_ranges):
            raise PolicyError(f"range {value!r} is not in the allowlist: {sorted(allowed_ranges)}")
