"""Minimal bounded MQTT 3.1.1 QoS1 publisher over mutually authenticated TLS.

No subscriptions, reconnects, broker routing, credential issuance or background loops.
"""

from __future__ import annotations

import socket
import ssl
from typing import Protocol


class Stream(Protocol):
    """Inject a bounded socket for protocol tests."""

    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


def _string(value: str) -> bytes:
    data = value.encode("utf-8")
    if not 1 <= len(data) <= 128 or b"\x00" in data:
        raise ValueError("invalid MQTT string")
    return len(data).to_bytes(2, "big") + data


def _frame(header: int, body: bytes) -> bytes:
    if len(body) > 4096:
        raise ValueError("packet exceeds experiment bound")
    length = len(body)
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        encoded.append(digit | (128 if length else 0))
        if not length:
            break
    return bytes([header]) + bytes(encoded) + body


class Publisher:
    """Sequential QoS1 client; PUBACK is transport evidence only."""

    def __init__(self, stream: Stream, client_id: str) -> None:
        self.stream = stream
        self.packet_id = 0
        stream.sendall(_frame(0x10, b"\x00\x04MQTT\x04\x02\x00\x3c" + _string(client_id)))
        if self._packet() != (0x20, b"\x00\x00"):
            raise ConnectionError("MQTT connection rejected")

    def _exact(self, count: int) -> bytes:
        result = bytearray()
        while len(result) < count:
            part = self.stream.recv(count - len(result))
            if not part:
                raise ConnectionError("MQTT connection closed")
            result.extend(part)
        return bytes(result)

    def _packet(self) -> tuple[int, bytes]:
        header = self._exact(1)[0]
        length = 0
        for index in range(4):
            digit = self._exact(1)[0]
            length += (digit & 127) * (128**index)
            if length > 4096:
                raise ConnectionError("MQTT response exceeds bound")
            if digit < 128:
                return header, self._exact(length)
        raise ConnectionError("invalid MQTT remaining length")

    def publish(self, topic: str, payload: bytes) -> None:
        """Wait for the matching PUBACK; do not retry ambiguous publication."""
        if self.packet_id >= 20:
            raise ValueError("publication limit reached")
        self.packet_id += 1
        identifier = self.packet_id.to_bytes(2, "big")
        self.stream.sendall(_frame(0x32, _string(topic) + identifier + payload))
        if self._packet() != (0x40, identifier):
            raise ConnectionError("missing or mismatched PUBACK")

    def close(self) -> None:
        """Close without retry or further application messages."""
        self.stream.close()


def connect(endpoint: str, client_id: str, ca: str, certificate: str, key: str) -> Publisher:
    """Use CA validation, hostname verification and client certificate on TLS/8883."""
    context = ssl.create_default_context(cafile=ca)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, key)
    raw = socket.create_connection((endpoint, 8883), timeout=5)
    try:
        stream = context.wrap_socket(raw, server_hostname=endpoint)
        try:
            return Publisher(stream, client_id)
        except Exception:
            stream.close()
            raise
    except Exception:
        raw.close()
        raise
