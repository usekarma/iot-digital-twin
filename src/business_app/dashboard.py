"""Offline localhost dashboard. Launch: python -m business_app.dashboard."""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
from collections import deque
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from business_app.grid_simulator import AssetEvent, GridSimulator, GridStateView, SimulatorConfig
from business_app.transition_trace import TickTrace

ASSETS = Path(__file__).with_name("dashboard_assets")
STATIC = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
}


class DashboardSession:
    """One bounded local rehearsal shared by all tabs; no background mutations."""

    def __init__(self) -> None:
        self.source = GridSimulator(SimulatorConfig())
        self.view = GridStateView(self.source.config)
        for event in self.source.snapshot():
            self.view.apply(event)
        self._trace: TickTrace | None = None
        self._history: deque[tuple[AssetEvent, ...]] = deque(maxlen=12)
        self._history.append(self.view.snapshot())

    def state(self) -> dict[str, object]:
        """Project current observations and bounded history into JSON-ready values."""
        events = self.view.snapshot()
        return {
            "source": "synthetic-local",
            "epoch": events[0].epoch,
            "tick": events[0].tick,
            "simulated_seconds": events[0].simulated_seconds,
            "assets": [asdict(e) | {"condition": e.condition} for e in events],
            "totals": {
                label: sum(e.condition == label for e in events)
                for label in ("HEALTHY", "WARNING", "CRITICAL")
            },
            "effects": [asdict(e) for e in self._trace.effects] if self._trace else [],
            "explanations": {
                e.asset_id: self._trace.explain(e.asset_id)
                if self._trace
                else "Known interview baseline. Step to observe a transition."
                for e in events
            },
            "history": [
                {
                    "epoch": row[0].epoch,
                    "tick": row[0].tick,
                    "severities": [e.severity for e in row],
                }
                for row in self._history
            ],
        }

    def step(self, epoch: int, tick: int) -> dict[str, object]:
        """Advance only the exact displayed generation/tick, never retry silently."""
        current = self.view.snapshot()[0]
        if (
            type(epoch) is not int
            or type(tick) is not int
            or (epoch, tick) != (current.epoch, current.tick)
        ):
            raise ValueError("stale or invalid step; refresh current state")
        trace = self.source.step_traced()
        for event in trace.observations:
            self.view.apply(event)
        self._trace = trace
        self._history.append(self.view.snapshot())
        return self.state()

    def reset(self, epoch: int, command_id: str) -> dict[str, object]:
        """Apply a reset receipt once; its duplicate never clears newer progress."""
        receipt = self.source.reset(command_id, expected_epoch=epoch)
        applied = self.view.reset(receipt)
        if applied:
            self._trace = None
            self._history.clear()
            self._history.append(self.view.snapshot())
        return {"state": self.state(), "receipt": asdict(receipt), "applied": applied}


class DashboardServer(HTTPServer):
    """Serial loopback server with a process-local request token."""

    def __init__(self, port: int) -> None:
        self.session = DashboardSession()
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), DashboardHandler)


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve only bundled files and bounded same-origin JSON commands."""

    server: DashboardServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress request logs; no token or request payload diagnostics."""

    def _send(self, status: int, data: bytes, mime: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, value: dict[str, object]) -> None:
        self._send(status, json.dumps(value).encode(), "application/json")

    def _host_allowed(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._json(403, {"error": "loopback Host required"})
        elif self.path == "/api/state":
            self._json(200, {"state": self.server.session.state(), "token": self.server.token})
        elif self.path in STATIC:
            name, mime = STATIC[self.path]
            self._send(200, (ASSETS / name).read_bytes(), mime)
        else:
            self._json(404, {"error": "unknown route"})

    def do_POST(self) -> None:
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        token = self.headers.get("X-Demo-Token", "")
        if (
            not self._host_allowed()
            or (origin is not None and origin != f"http://{host}")
            or not hmac.compare_digest(token.encode(), self.server.token.encode())
        ):
            self._json(403, {"error": "same-origin local command required"})
            return
        if self.path not in ("/api/step", "/api/reset"):
            self._json(404, {"error": "unknown route"})
            return
        if self.headers.get("Content-Type") != "application/json":
            self._json(415, {"error": "application/json required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid body length"})
            return
        if not 1 <= length <= 256 or self.headers.get("Transfer-Encoding") is not None:
            self._json(413, {"error": "body must be 1–256 bytes without transfer encoding"})
            return
        try:
            data = json.loads(self.rfile.read(length))
            fields = {"epoch", "tick"} if self.path == "/api/step" else {"epoch", "command_id"}
            if not isinstance(data, dict) or set(data) != fields:
                raise ValueError("unexpected command fields")
        except (ValueError, UnicodeError):
            self._json(400, {"error": "invalid JSON command"})
            return
        result: dict[str, object]
        try:
            if self.path == "/api/step":
                result = {"state": self.server.session.step(data["epoch"], data["tick"])}
            else:
                result = self.server.session.reset(data["epoch"], data["command_id"])
        except ValueError as exc:
            self._json(409, {"error": str(exc)})
            return
        self._json(200, result)


def make_server(port: int = 8765) -> DashboardServer:
    """Construct the loopback server; port zero is supported for isolated tests."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in [0, 65535]")
    return DashboardServer(port)


def main() -> None:
    """Run until interrupted; state exists only for this process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        server = make_server(args.port)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Offline IoT dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
