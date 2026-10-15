"""Private UART provisioning and bounded button arm; requires flash/publication approval."""

import argparse
import json
import secrets
import stat
import time
from pathlib import Path


def private_text(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Provisioning files must be regular private files (mode 0600)")
    return path.read_text()


def write_config_paced(port, encoded: bytes) -> None:
    """Send one configuration frame in small chunks; never retry or arm."""
    for offset in range(0, len(encoded), 32):
        chunk = encoded[offset : offset + 32]
        if port.write(chunk) != len(chunk):
            raise RuntimeError("Incomplete configuration write; not armed")
        port.flush()
        time.sleep(0.02)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--arm-button", action="store_true", required=True)
    args = parser.parse_args()
    cfg = json.loads(private_text(args.config))
    frame = {
        "ssid": cfg["ssid"],
        "wifi_password": cfg["wifi_password"],
        "endpoint": cfg["endpoint"],
        "certificate_pem": private_text(Path(cfg["certificate_path"])),
        "private_key_pem": private_text(Path(cfg["private_key_path"])),
        "nonce": secrets.token_hex(16),
        "epoch": int(time.time()),
    }
    encoded = ("CONFIG " + json.dumps(frame, separators=(",", ":")) + "\n").encode()
    if len(encoded) > 8193:
        raise ValueError("Provisioning frame exceeds firmware bound")
    import serial

    port = serial.Serial(port=None, baudrate=115200, timeout=0.25, write_timeout=5)
    port.dtr = False
    port.rts = False
    port.port = args.port
    with port:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if port.readline().strip() == b"ATOM_BUTTON_V1 READY":
                break
        else:
            raise RuntimeError("Reviewed ATOM firmware banner not observed; no credentials sent")
        write_config_paced(port, encoded)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            line = port.readline().strip()
            if line == b"CONFIG_READY":
                break
            if line == b"CONFIG_REJECTED":
                raise RuntimeError("Configuration was rejected; not armed")
        else:
            raise RuntimeError("Configuration was not accepted; not armed")
        if port.write(b"ARM_BUTTON\n") != 11:
            raise RuntimeError("Partial arm write; do not retry")
        port.flush()
        print("Expected session ID:", frame["nonce"], flush=True)
        expected_sequence = 1
        pending = False
        deadline = time.monotonic() + 200
        while time.monotonic() < deadline:
            line = port.readline().strip()
            if line in (b"BUTTON_ARMED", b"WIFI_READY", b"TLS_READY", b"MQTT_READY"):
                print(line.decode(), flush=True)
            elif line.startswith(b"EVENT "):
                data = json.loads(line[6:])
                if pending or data != {
                    "device_id": "atom-lite-001",
                    "event": "button_press",
                    "session_id": frame["nonce"],
                    "event_id": frame["nonce"] + "-" + str(expected_sequence),
                    "sequence": expected_sequence,
                }:
                    raise RuntimeError("Unexpected event contract; do not retry")
                pending = True
                print(json.dumps(data), flush=True)
            elif line == b"PUBACK_RECEIVED":
                if not pending:
                    raise RuntimeError("Unexpected acknowledgement")
                pending = False
                expected_sequence += 1
                print("PUBACK_RECEIVED; confirm exact event ID in AWS", flush=True)
            elif line in (b"SESSION_COMPLETE", b"SESSION_EXPIRED"):
                if pending:
                    raise RuntimeError("Unacknowledged event; do not retry")
                print(line.decode(), flush=True)
                return
            elif line.startswith(b"ERROR_") or line in (
                b"PUBLICATION_UNKNOWN",
                b"COMMAND_REJECTED",
                b"ARM_REJECTED",
            ):
                raise RuntimeError("Failed or unknown attempt; no automatic retry")
        raise RuntimeError("Session result unknown; no automatic retry")


if __name__ == "__main__":
    main()
