# Offline IoT demonstration

Owner: Ted / repository maintainer. Requires Python 3.12 and a browser; no runtime
dependency installation, frontend build, internet connection, AWS or device access.

From the repository root:

```bash
make dashboard
```

Open http://127.0.0.1:8765. Keep the terminal running; Ctrl+C stops the server.
For a busy port: `PYTHONPATH=src python3 -m business_app.dashboard --port 8766`.
The server always binds IPv4 loopback; it cannot be configured to expose the network.
No browser opens automatically. All fonts and assets are local/system resources.

## One-minute talk track

- 0–15 seconds: identify the Synthetic / Offline badge, baseline totals, ring and
  recent severity history. Asset-000 starts critical; asset-001 starts healthy.
- 15–30 seconds: Step twice or Play. Asset-001 becomes warning then critical.
  Highlighted arrows use the recorded pre-tick propagation effects. Play runs one
  tick per second and pauses at tick 6; Pause can stop it sooner.
- 30–45 seconds: select asset-001; explain the exact predecessor input and arithmetic.
  History shows persistent deterioration; this is a fictional model, not power-flow proof.
- 45–60 seconds: Reset baseline; confirm restored totals, tick 0, new epoch, and
  cleared recent history. This receipt proves local application only, not cloud/device ACK.

This is a suggested script, not a measured human rehearsal. Select any asset by click
or keyboard Enter/Space. Step is independent of Play; Reset and manual Step pause Play.

## Bounds and recovery

Five assets, fixed seed 17, 12 recent snapshots, latest trace only, existing 1000-tick
domain cap. Server has no background simulation; browser Play drives sequential requests.
Closing/reloading pauses browser progression. Tabs share one session: stale commands
fail rather than retry; reload to reconcile state after another tab changes it.
Reset clears the current epoch history and restores the interview baseline, including
its initial warning/critical assets. Restart starts a new isolated session with epoch 1.
No durable storage, cloud authorization or production availability claim.

Request token, loopback Host checks, same-origin mutation checks, 256-byte body cap and
three-second socket read timeout protect this local demo boundary. Don't expose it
through a proxy/tunnel or feed it real secrets. No automatic cloud/hardware fallback.

Tests: `PYTHONPATH=src python -m pytest tests/test_dashboard.py`. Full quality gates:
`PYTHONPATH=src python scripts/check.py` in the existing verification environment.
Use a clean checkout for release verification: the original workspace's ignored public
mbedTLS fixture ELF still matches its credential test; no exception is added here.

Subsequent milestones: reviewer approval, timed rehearsal/recording, optional debugging
exercise, then separately reviewed cloud and ATOM application-ACK integration.
