import pytest

from ttl_broker.policy import PolicyError, check

RANGES = frozenset({"TTL-1", "TTL-2"})


def allowed(method, path, query=None, body=None):
    return check(method, path, query or {}, body, RANGES)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/user/credentials"),
        ("POST", "/user/credentials"),
        ("GET", "/user/apikey"),
        ("GET", "/user/wireguard"),
        ("GET", "/vm/console/ticket"),
        ("GET", "/vm/console/view"),
        ("POST", "/user"),
        ("GET", "/user/all"),
        ("DELETE", "/user/bob"),
        ("POST", "/ranges/assign/bob/TTL-1"),
        ("POST", "/groups"),
        ("PUT", "/user/quotas"),
        ("POST", "/migrate/sdn"),
        ("POST", "/antisandbox/install-custom"),
        ("POST", "/kms/install"),
        ("GET", "/diagnostics"),
        ("POST", "/blueprints/bp1/share/users"),
    ],
)
def test_credential_and_admin_operations_are_blocked(method, path):
    with pytest.raises(PolicyError, match="not allowed"):
        allowed(method, path, {"rangeID": "TTL-1"})


@pytest.mark.parametrize(
    "path",
    ["/template/debian-12-x64-server-template", "/blueprints/bp1", "/sources/src1"],
)
def test_deleting_shared_objects_is_blocked(path):
    with pytest.raises(PolicyError, match="not allowed"):
        allowed("DELETE", path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/ansible/role"),
        ("POST", "/ansible/collection"),
        ("PATCH", "/ansible/role/scope"),
        ("POST", "/ansible/subscription-roles"),
        ("POST", "/sources/src1/install"),
        ("POST", "/blueprints/bp1/install"),
    ],
)
def test_changing_shared_roles_is_blocked(method, path):
    with pytest.raises(PolicyError, match="not allowed"):
        allowed(method, path)


def test_reading_roles_is_allowed():
    allowed("GET", "/ansible")
    allowed("POST", "/ansible/role/vars")


def test_unknown_operation_is_blocked():
    with pytest.raises(PolicyError, match="not allowed"):
        allowed("GET", "/something/new")


def test_range_operation_in_allowlist_passes():
    allowed("POST", "/snapshots/rollback", {"rangeID": "TTL-1"}, {"name": "clean"})


def test_range_operation_requires_explicit_range():
    with pytest.raises(PolicyError, match="rangeID is required"):
        allowed("PUT", "/range/poweron")


def test_range_operation_outside_allowlist_is_blocked():
    with pytest.raises(PolicyError, match="not in the allowlist"):
        allowed("PUT", "/range/poweroff", {"rangeID": "Other"})


def test_range_in_path_is_checked():
    allowed("DELETE", "/range/TTL-2/vms")
    with pytest.raises(PolicyError, match="not in the allowlist"):
        allowed("DELETE", "/range/Other/vms")


def test_range_in_body_is_checked():
    allowed("POST", "/ranges/create", body={"name": "x", "rangeID": "TTL-2"})
    with pytest.raises(PolicyError, match="not in the allowlist"):
        allowed("POST", "/blueprints/bp1/apply", body={"rangeID": "Other"})
    with pytest.raises(PolicyError, match="rangeID is required"):
        allowed("POST", "/ranges/create", body={"name": "x"})


def test_optional_range_is_still_checked():
    allowed("GET", "/whoami")
    with pytest.raises(PolicyError, match="not in the allowlist"):
        allowed("GET", "/whoami", {"rangeID": "Other"})


@pytest.mark.parametrize(
    ("query", "body"),
    [({"rangeID": "TTL-1", "userID": "bob"}, None), ({"rangeID": "TTL-1"}, {"userID": "bob"})],
)
def test_acting_as_another_user_is_blocked(query, body):
    with pytest.raises(PolicyError, match="userID"):
        allowed("GET", "/range", query, body)


@pytest.mark.parametrize(
    "path",
    ["/range/../user/apikey", "/range//config", "/range/config?userID=bob", "/range/%2e%2e/vms", "range"],
)
def test_malformed_paths_are_blocked(path):
    with pytest.raises(PolicyError):
        allowed("GET", path, {"rangeID": "TTL-1"})


def test_method_is_case_insensitive():
    allowed("get", "/range", {"rangeID": "TTL-1"})


def test_non_string_range_is_blocked():
    with pytest.raises(PolicyError, match="not in the allowlist"):
        allowed("GET", "/range", {"rangeID": ["TTL-1"]})
