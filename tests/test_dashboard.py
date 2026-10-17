import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from business_app.dashboard import DashboardSession, make_server


def test_dashboard_progression_and_bounded_history() -> None:
    first, second = DashboardSession(), DashboardSession()
    assert first.state()["totals"] == {"HEALTHY": 3, "WARNING": 1, "CRITICAL": 1}
    for tick in range(20):
        first.step(1, tick)
        second.step(1, tick)
        assert first.state() == second.state()
    state = first.state()
    assert len(state["history"]) == 12
    assert state["assets"][1]["condition"] == "CRITICAL"
    assert "asset-000 was CRITICAL" in state["explanations"]["asset-001"]


def test_dashboard_reset_duplicate_and_stale_requests() -> None:
    session = DashboardSession()
    session.step(1, 0)
    result = session.reset(1, "reset-1")
    assert result["applied"]
    assert session.state()["epoch"] == 2
    assert session.state()["tick"] == 0
    assert len(session.state()["history"]) == 1
    session.step(2, 0)
    before = session.state()
    assert not session.reset(1, "reset-1")["applied"]
    assert session.state() == before
    for epoch, tick in [(1, 1), (2, 0), (True, 1)]:
        with pytest.raises(ValueError):
            session.step(epoch, tick)
        assert session.state() == before
    with pytest.raises(ValueError):
        session.reset(1, "other")
    with pytest.raises(ValueError):
        session.reset(2, "../bad")
    assert session.state() == before


@pytest.fixture
def server():
    instance = make_server(0)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=3)


def request(server, path, body=None, **headers):
    url = f"http://127.0.0.1:{server.server_port}{path}"
    if body is not None:
        headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=body, headers=headers)
    return urlopen(req, timeout=3)


def test_loopback_routes_and_assets(server) -> None:
    assert server.server_address[0] == "127.0.0.1"
    for path, content in [
        ("/", b"Synthetic"),
        ("/app.js", b"fetch"),
        ("/style.css", b"background"),
    ]:
        with request(server, path) as response:
            assert content in response.read()
    with pytest.raises(HTTPError) as error:
        request(server, "/../../pyproject.toml")
    assert error.value.code == 404
    with pytest.raises(HTTPError) as error:
        request(server, "/", Host="evil.example")
    assert error.value.code == 403


def test_http_mutations_and_negative_cases(server) -> None:
    with request(server, "/api/state") as response:
        initial = json.load(response)
    token = initial["token"]
    body = json.dumps({"epoch": 1, "tick": 0}).encode()
    for data, headers, status in [
        (body, {}, 403),
        (body, {"X-Demo-Token": token, "Origin": "http://evil.example"}, 403),
        (b"{}" * 200, {"X-Demo-Token": token}, 413),
        (b"not json", {"X-Demo-Token": token}, 400),
        (b"{}", {"X-Demo-Token": token}, 400),
        (body, {"X-Demo-Token": token, "Content-Type": "text/plain"}, 415),
    ]:
        with pytest.raises(HTTPError) as error:
            request(server, "/api/step", data, **headers)
        assert error.value.code == status
    assert server.session.state()["tick"] == 0
    with request(server, "/api/step", body, **{"X-Demo-Token": token}) as response:
        assert json.load(response)["state"]["tick"] == 1
    with pytest.raises(HTTPError) as error:
        request(server, "/api/step", body, **{"X-Demo-Token": token})
    assert error.value.code == 409
    reset = json.dumps({"epoch": 1, "command_id": "browser-reset"}).encode()
    with request(server, "/api/reset", reset, **{"X-Demo-Token": token}) as response:
        assert json.load(response)["applied"]
    with request(server, "/api/reset", reset, **{"X-Demo-Token": token}) as response:
        assert not json.load(response)["applied"]


@pytest.mark.parametrize("port", [-1, 65536, True, "8765"])
def test_invalid_port_rejected_before_binding(port) -> None:
    with pytest.raises(ValueError):
        make_server(port)


def test_projection_is_a_copy_not_mutable_session_state() -> None:
    session = DashboardSession()
    snapshot = session.state()
    snapshot["history"][0]["severities"][0] = 0
    snapshot["assets"][0]["severity"] = 0
    assert session.state()["assets"][0]["severity"] == 2
    assert session.state()["history"][0]["severities"][0] == 2


def test_http_unknown_mutation_and_invalid_epoch(server) -> None:
    with request(server, "/api/state") as response:
        token = json.load(response)["token"]
    for route, body, code in [
        ("/unknown", b"{}", 404),
        ("/api/step", b'{"epoch":true,"tick":0}', 409),
        ("/api/reset", b'{"epoch":1,"command_id":"../bad"}', 409),
        ("/api/step", b"[]", 400),
    ]:
        with pytest.raises(HTTPError) as error:
            request(server, route, body, **{"X-Demo-Token": token})
        assert error.value.code == code
    assert server.session.state()["tick"] == 0
