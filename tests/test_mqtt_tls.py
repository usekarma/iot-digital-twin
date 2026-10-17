import pytest

from business_app.mqtt_tls import Publisher


class FakeStream:
    def __init__(self, incoming):
        self.incoming = bytearray(incoming)
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        result = self.incoming[: min(size, 1)]
        del self.incoming[: len(result)]
        return bytes(result)

    def close(self):
        self.closed = True


def test_fragmented_connack_and_matching_qos1_ack():
    stream = FakeStream(b"\x20\x02\x00\x00\x40\x02\x00\x01")
    client = Publisher(stream, "adage-operational-m1")
    client.publish("test/topic", b"synthetic")
    assert stream.sent[0].startswith(b"\x10")
    assert stream.sent[1][0] == 0x32
    client.close()
    assert stream.closed


@pytest.mark.parametrize("response", [b"", b"\x20\x02\x00\x05", b"\x20\xff\xff\xff\xff"])
def test_rejected_closed_and_oversized_connections_fail(response):
    with pytest.raises(ConnectionError):
        Publisher(FakeStream(response), "adage-operational-m1")


def test_mismatched_ack_stops_without_retry():
    stream = FakeStream(b"\x20\x02\x00\x00\x40\x02\x00\x02")
    client = Publisher(stream, "adage-operational-m1")
    with pytest.raises(ConnectionError):
        client.publish("test/topic", b"synthetic")
    assert len(stream.sent) == 2


def test_tls_verifies_hostname_ca_and_uses_client_certificate(monkeypatch):
    from business_app import mqtt_tls

    stream = FakeStream(b"\x20\x02\x00\x00")
    calls = []

    class Context:
        minimum_version = None

        def load_cert_chain(self, cert, key):
            calls.append((cert, key))

        def wrap_socket(self, raw, server_hostname):
            calls.append(server_hostname)
            return stream

    context = Context()
    monkeypatch.setattr(mqtt_tls.ssl, "create_default_context", lambda cafile: context)
    monkeypatch.setattr(mqtt_tls.socket, "create_connection", lambda address, timeout: stream)
    client = mqtt_tls.connect("endpoint", "client", "ca", "cert", "key")
    assert calls == [("cert", "key"), "endpoint"]
    assert context.minimum_version == mqtt_tls.ssl.TLSVersion.TLSv1_2
    client.close()
