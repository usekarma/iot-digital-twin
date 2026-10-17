import json
from types import SimpleNamespace

import pytest

from business_app import operational_cli as cli
from business_app.operational_publisher import envelopes
from business_app.sitewise_readback import verify


@pytest.fixture(autouse=True)
def mock_cli_location(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/aws")


def test_dry_run_has_no_network_and_refuses_overwrite(monkeypatch, tmp_path):
    target = tmp_path / "manifest.json"
    monkeypatch.setattr("sys.argv", ["publisher", "--manifest", str(target)])
    monkeypatch.setattr(cli, "connect", lambda *a: pytest.fail("network forbidden"))
    cli.main()
    assert json.loads(target.read_text())["live_attempted"] is False
    with pytest.raises(FileExistsError):
        cli.main()


def live_args(target):
    return [
        "publisher",
        "--manifest",
        str(target),
        "--execute-approved-publish",
        "--endpoint",
        "synthetic-ats.iot.us-east-1.amazonaws.com",
        "--profile",
        "synthetic",
        "--region",
        "us-east-1",
        "--expected-account",
        "000000000000",
        "--ca",
        "ca",
        "--certificate",
        "cert",
        "--key",
        "key",
    ]


def test_live_target_mismatch_stops_before_mqtt(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", live_args(tmp_path / "manifest.json"))
    monkeypatch.setattr(
        cli.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout='{"Account":"111111111111"}')
    )
    monkeypatch.setattr(cli, "connect", lambda *a: pytest.fail("no MQTT on mismatch"))
    with pytest.raises(SystemExit):
        cli.main()


def test_approved_boundary_with_fake_transport(monkeypatch, tmp_path):
    sent = []
    closed = []
    monkeypatch.setattr("sys.argv", live_args(tmp_path / "manifest.json"))
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda argv, **k: SimpleNamespace(
            stdout='{"Account":"000000000000"}'
            if "sts" in argv
            else '{"endpointAddress":"synthetic-ats.iot.us-east-1.amazonaws.com"}'
        ),
    )
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *a: SimpleNamespace(
            publish=lambda *p: sent.append(p), close=lambda: closed.append(True)
        ),
    )
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    cli.main()
    assert len(sent) == 20 and closed == [True]


def test_readback_requires_exact_good_history_and_actual_attempt():
    packets = envelopes("a" * 32, 1_800_000_000)
    manifest = {"live_attempted": True, "observations": packets}
    history = {
        "assetPropertyValueHistory": [
            {
                "timestamp": {"timeInSeconds": p["event_time_seconds"], "offsetInNanos": 0},
                "quality": "GOOD",
                "value": {"integerValue": p["severity"]},
            }
            for p in packets
        ]
    }
    assert verify(manifest, history) == 20
    for bad in [history | {"nextToken": "more"}, {"assetPropertyValueHistory": []}]:
        with pytest.raises(ValueError):
            verify(manifest, bad)
    with pytest.raises(ValueError):
        verify(manifest | {"live_attempted": False}, history)
    history["assetPropertyValueHistory"][0]["value"]["integerValue"] = True
    with pytest.raises(ValueError):
        verify(manifest, history)
