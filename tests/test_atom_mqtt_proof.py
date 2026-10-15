"""Host verification of one-shot ATOM MQTT wire contract; no hardware or AWS."""

import runpy
import subprocess
from pathlib import Path

import pytest


def test_native_atom_mqtt_protocol(tmp_path: Path) -> None:
    firmware = Path(__file__).resolve().parents[1] / "firmware" / "atom-lite-mqtt"
    executable = tmp_path / "contract"
    subprocess.run(
        [
            "g++",
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(firmware / "include"),
            str(firmware / "test" / "native_contract.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(executable)], check=True, capture_output=True)


def test_private_serial_inputs_reject_public_permissions_and_symlinks(tmp_path: Path) -> None:
    helper = Path(__file__).resolve().parents[1] / "firmware/atom-lite-mqtt/tools/send_once.py"
    private_text = runpy.run_path(str(helper))["private_text"]
    source = tmp_path / "input.txt"
    source.write_text("synthetic configuration")
    source.chmod(0o600)
    assert private_text(source) == "synthetic configuration"
    source.chmod(0o644)
    with pytest.raises(ValueError):
        private_text(source)
    source.chmod(0o600)
    link = tmp_path / "link.txt"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        private_text(link)


def test_paced_configuration_exact_bytes_and_no_partial_write_retry(monkeypatch) -> None:
    helper = Path(__file__).resolve().parents[1] / "firmware/atom-lite-mqtt/tools/send_once.py"
    send = runpy.run_path(str(helper))["write_config_paced"]
    waits = []
    monkeypatch.setattr("time.sleep", waits.append)

    class Port:
        def __init__(self, short=False):
            self.parts = []
            self.short = short
            self.flushes = 0

        def write(self, data):
            self.parts.append(data)
            return len(data) - int(self.short)

        def flush(self):
            self.flushes += 1

    frame = b"CONFIG " + b"x" * 1400 + b"\n"
    port = Port()
    send(port, frame)
    assert b"".join(port.parts) == frame
    assert max(map(len, port.parts)) <= 32
    assert port.flushes == len(waits) == len(port.parts)
    assert all(delay == 0.02 for delay in waits)
    short = Port(short=True)
    with pytest.raises(RuntimeError, match="Incomplete configuration"):
        send(short, frame)
    assert len(short.parts) == 1
