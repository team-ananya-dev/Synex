import pytest

from app.core.operator_auth import is_operator_route
from tests.test_runner import api, start  # noqa: F401  (fixtures and helpers)


@pytest.mark.parametrize("method,path,protected", [
    ("GET", "/approvals", True), ("GET", "/audit/events", True), ("GET", "/audit/verify", True), ("GET", "/costs", True),
    ("GET", "/operator/responses", True), ("POST", "/operator/responses/R1/decide", True), ("GET", "/mailbox", True),
    ("GET", "/cases", True), ("GET", "/cases/abc", True), ("GET", "/cases/abc/events", True), ("POST", "/cases/abc/retry", True),
    ("GET", "/cases/abc/costs", True),
    ("POST", "/cases", False), ("GET", "/customer/cases/abc", False), ("GET", "/customer/cases/abc/events", False),
    ("POST", "/customer/cases/abc/approve-outreach", False), ("GET", "/expert/tok", False), ("GET", "/health", False),
    ("OPTIONS", "/approvals", False),
])
def test_which_routes_are_operator_only(method, path, protected):
    assert is_operator_route(method, path) is protected


def test_operator_key_is_required_when_set(api, monkeypatch):
    client, _ = api
    cid = start(client)                                         # asking and approving are the customer's: no key
    monkeypatch.setenv("SYNEX_OPERATOR_KEY", "s3cret")
    assert client.get("/approvals").status_code == 401
    assert client.get("/approvals", headers={"X-Operator-Key": "wrong"}).status_code == 401
    assert client.get("/approvals", headers={"X-Operator-Key": "s3cret"}).status_code == 200
    assert client.get(f"/cases/{cid}").status_code == 401
    assert client.get(f"/customer/cases/{cid}").status_code == 200
    with client.stream("GET", f"/cases/{cid}/events?key=s3cret") as r:
        assert r.status_code == 200


def test_no_key_set_means_open_for_local_development(api, monkeypatch):
    client, _ = api
    monkeypatch.delenv("SYNEX_OPERATOR_KEY", raising=False)
    assert client.get("/approvals").status_code == 200
