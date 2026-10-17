import json

import pytest

from business_app.operational_publisher import envelopes, publish_run


def test_twenty_observations_preserve_model_and_unique_real_timestamps():
    packets = envelopes("a" * 32, 1_800_000_000)
    assert len(packets) == 20
    assert [p["sequence"] for p in packets] == list(range(1, 21))
    assert len({p["event_time_seconds"] for p in packets}) == 20
    assert packets == envelopes("a" * 32, 1_800_000_000)
    for p in packets:
        assert p["synthetic"] is True
        assert p["asset_id"] == "asset-000"
        assert p["observation"] == {
            k: p[k] for k in ("asset_id", "epoch", "sequence", "tick", "severity")
        }


def test_invalid_run_inputs():
    for run, start in [("wrong", 1_800_000_000), ("a" * 32, True), ("a" * 32, -1)]:
        with pytest.raises(ValueError):
            envelopes(run, start)


def test_injected_transport_pacing_and_fail_stop():
    sent = []
    sleeps = []
    packets = envelopes("a" * 32, 1_800_000_000)
    publish_run(
        packets, lambda topic, payload: sent.append((topic, json.loads(payload))), sleeps.append
    )
    assert len(sent) == 20
    assert sleeps == [1.0] * 19
    assert all(topic.endswith("asset-000/telemetry") for topic, _ in sent)
    calls = []

    def failed(topic, payload):
        calls.append(topic)
        raise TimeoutError

    with pytest.raises(TimeoutError):
        publish_run(packets, failed, sleeps.append)
    assert len(calls) == 1


def test_modified_payload_rejected_before_transport():
    for field, value in [("severity", True), ("severity", 9), ("extra", "unexpected")]:
        packets = envelopes("a" * 32, 1_800_000_000)
        packets[0][field] = value
        with pytest.raises(ValueError):
            publish_run(packets, lambda *_: pytest.fail("invalid publish"), lambda _: None)
