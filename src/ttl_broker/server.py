"""MCP server that gives agents the Ludus API without the Ludus key.

Configuration comes from the environment:

    LUDUS_URL             e.g. https://198.51.100.1:8080
    LUDUS_API_KEY_FILE    file holding the Ludus key (or LUDUS_API_KEY)
    LUDUS_ALLOWED_RANGES  comma-separated range IDs agents may use
    LUDUS_CA_FILE         CA bundle for the Ludus certificate, or
    LUDUS_INSECURE_TLS=1  to skip verification
    BROKER_TOKEN          bearer token agents send to this server
    BROKER_HOST           listen address (default 0.0.0.0)
    BROKER_PORT           listen port (default 8765)
"""

import base64
import hmac
import logging
import os
import sys
from typing import Any

import httpx
import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ttl_broker.policy import OPERATIONS, PolicyError, check

log = logging.getLogger("ttl_broker")

MAX_TEXT = 200_000
TEXT_TYPES = ("text/", "json", "yaml", "xml")


class Broker:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        allowed_ranges: frozenset[str],
        verify: str | bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key
        self.allowed_ranges = allowed_ranges
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/api/v2",
            headers={"X-API-KEY": api_key},
            verify=verify,
            timeout=120,
            transport=transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        query: dict[str, Any],
        body: dict[str, Any] | None,
        file_text: str | None = None,
    ) -> dict[str, Any]:
        check(method, path, query, body, self.allowed_ranges)
        if file_text is not None:
            sent = {"data": body or {}, "files": {"file": ("range-config.yml", file_text)}}
        else:
            sent = {"json": body} if body is not None else {}
        response = await self.client.request(method.upper(), path, params=query, **sent)
        log.info("%s %s rangeID=%s -> %s", method.upper(), path, query.get("rangeID"), response.status_code)

        content_type = response.headers.get("content-type", "")
        result: dict[str, Any] = {"status": response.status_code, "content_type": content_type}
        if any(t in content_type for t in TEXT_TYPES):
            text = response.text.replace(self.api_key, "[REDACTED]")
            if len(text) > MAX_TEXT:
                text, result["truncated"] = text[:MAX_TEXT], True
            result["body"] = text
        else:
            result["encoding"] = "base64"
            result["body"] = base64.b64encode(response.content).decode()
        return result


def require_token(app, token: str):
    """Wrap an ASGI app so every HTTP request needs `Authorization: Bearer <token>`."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            given = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(given, expected):
                await send({"type": "http.response.start", "status": 401, "headers": []})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await app(scope, receive, send)

    return guarded


def build_server(broker: Broker) -> MCPServer:
    server = MCPServer(
        "ludus-broker",
        instructions=(
            "Calls the Ludus API v2 for you. Credential-returning and admin operations are blocked, "
            f"and range operations must name one of these ranges with rangeID: {sorted(broker.allowed_ranges)}. "
            "Use list_operations to see what is allowed, and GET /openapi for request details."
        ),
    )

    @server.tool()
    def list_operations() -> dict[str, Any]:
        """List the Ludus operations this broker allows and the ranges agents may use."""
        return {
            "allowed_ranges": sorted(broker.allowed_ranges),
            "operations": [
                f"{method} {path}" + (f" (rangeID in {where})" if where else "") for method, path, where in OPERATIONS
            ],
        }

    @server.tool()
    async def ludus_request(
        method: str,
        path: str,
        query: dict[str, str | int | bool] | None = None,
        body: dict[str, Any] | None = None,
        file_text: str | None = None,
    ) -> dict[str, Any]:
        """Call one Ludus API v2 operation, such as GET /range or POST /snapshots/rollback.

        path is relative to /api/v2 with no query string; put rangeID and other query
        parameters in query. body is the JSON body. For PUT /range/config, pass the YAML
        in file_text and any form fields (like force) in body. Binary responses come
        back base64-encoded.
        """
        try:
            return await broker.request(method, path, query or {}, body, file_text)
        except PolicyError as exc:
            raise ToolError(str(exc)) from exc
        except httpx.TransportError as exc:
            raise ToolError(f"could not reach Ludus: {type(exc).__name__}") from exc

    return server


def api_key_from_env(env) -> str:
    if env.get("LUDUS_API_KEY_FILE"):
        with open(env["LUDUS_API_KEY_FILE"]) as f:
            return f.read().strip()
    if env.get("LUDUS_API_KEY"):
        return env["LUDUS_API_KEY"]
    sys.exit("set LUDUS_API_KEY_FILE or LUDUS_API_KEY")


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(message)s")
    env = os.environ
    ranges = frozenset(r.strip() for r in env["LUDUS_ALLOWED_RANGES"].split(",") if r.strip())
    if not ranges:
        sys.exit("LUDUS_ALLOWED_RANGES must name at least one range")
    if env.get("LUDUS_CA_FILE"):
        verify: str | bool = env["LUDUS_CA_FILE"]
    elif env.get("LUDUS_INSECURE_TLS") == "1":
        verify = False
    else:
        sys.exit("set LUDUS_CA_FILE, or LUDUS_INSECURE_TLS=1 to skip certificate checks")

    broker = Broker(env["LUDUS_URL"], api_key_from_env(env), ranges, verify)
    host = env.get("BROKER_HOST", "0.0.0.0")
    app = build_server(broker).streamable_http_app(host=host)
    uvicorn.run(require_token(app, env["BROKER_TOKEN"]), host=host, port=int(env.get("BROKER_PORT", "8765")))
