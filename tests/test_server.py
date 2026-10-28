import base64

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ttl_broker.policy import PolicyError
from ttl_broker.server import Broker, require_token

KEY = "ludus-secret-key"


def make_broker(handler):
    return Broker(
        "https://ludus.test:8080",
        KEY,
        frozenset({"TTL-1"}),
        transport=httpx.MockTransport(handler),
    )


async def test_forwards_allowed_call_with_key_and_range():
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"ok": True})

    result = await make_broker(handler).request("POST", "/snapshots/rollback", {"rangeID": "TTL-1"}, {"name": "clean"})

    request = seen["request"]
    assert request.url.path == "/api/v2/snapshots/rollback"
    assert request.url.params["rangeID"] == "TTL-1"
    assert request.headers["X-API-KEY"] == KEY
    assert request.content == b'{"name":"clean"}'
    assert result == {"status": 200, "content_type": "application/json", "body": '{"ok":true}'}


async def test_blocked_call_never_reaches_ludus():
    def handler(request):
        raise AssertionError("should not be called")

    with pytest.raises(PolicyError):
        await make_broker(handler).request("GET", "/user/apikey", {}, None)


async def test_scrubs_ludus_key_from_responses():
    def handler(request):
        return httpx.Response(500, text=f"bad header X-API-KEY: {KEY}")

    result = await make_broker(handler).request("GET", "/range", {"rangeID": "TTL-1"}, None)

    assert KEY not in result["body"]
    assert "[REDACTED]" in result["body"]
    assert result["status"] == 500


async def test_binary_response_is_base64():
    def handler(request):
        return httpx.Response(200, content=b"PK\x03\x04", headers={"content-type": "application/zip"})

    result = await make_broker(handler).request("GET", "/range/rdpconfigs", {"rangeID": "TTL-1"}, None)

    assert result["encoding"] == "base64"
    assert base64.b64decode(result["body"]) == b"PK\x03\x04"


async def test_file_text_is_sent_as_multipart():
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={})

    await make_broker(handler).request(
        "PUT", "/range/config", {"rangeID": "TTL-1"}, {"force": "true"}, file_text="ludus: []\n"
    )

    request = seen["request"]
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b"ludus: []" in request.content
    assert b'name="force"' in request.content


def test_require_token():
    inner = Starlette(routes=[Route("/mcp", lambda r: PlainTextResponse("hi"), methods=["GET"])])
    client = TestClient(require_token(inner, "s3cret"))

    assert client.get("/mcp").status_code == 401
    assert client.get("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/mcp", headers={"Authorization": "Bearer s3cret"}).text == "hi"


async def test_tool_reports_why_a_call_was_blocked():
    from mcp import Client

    from ttl_broker.server import build_server

    broker = make_broker(lambda request: httpx.Response(200, json={}))
    async with Client(build_server(broker)) as client:
        result = await client.call_tool("ludus_request", {"method": "GET", "path": "/user/credentials"})

    assert result.is_error
    assert "not allowed by the broker policy" in result.content[0].text


async def test_tool_reports_ludus_unreachable():
    from mcp import Client

    from ttl_broker.server import build_server

    def handler(request):
        raise httpx.ConnectError("refused")

    async with Client(build_server(make_broker(handler))) as client:
        result = await client.call_tool("ludus_request", {"method": "GET", "path": "/range", "query": {"rangeID": "TTL-1"}})

    assert result.is_error
    assert "could not reach Ludus" in result.content[0].text
