# Offline IoT interview dashboard — Issue #17

Status: local demonstration proposal. Owner: Ted / repository maintainer.
Baseline: terminal simulator/traces from PR #19/#20. Target: a visible progression and
reset explainable within 60 seconds, without cloud, network assets or device operations.

## Contract

One command starts a standard-library HTTPServer on IPv4 loopback 127.0.0.1:8765.
Only the port is configurable; no external bind option. Bundled HTML/CSS/JS and system
fonts work offline. The five-asset, seed-17 preset is unchanged. Python owns one
single-threaded in-memory simulator and current-state consumer shared by browser tabs.
Browser Play sends sequential Step requests once per second, pauses after tick 6,
and cancels on error or Reset. Step stays manually available within existing tick bounds.

The page shows synthetic/local labels, health totals, the directed asset ring,
propagation from actual previous-tick trace effects, selected-asset explanation,
tick/epoch, and a recent severity heatmap of at most 12 snapshots. No trace history
is retained beyond the latest trace. Reset clears visible history and loads the
known baseline in a new epoch; duplicate receipt delivery must not erase progress.
A reset is a local application result, never a cloud or physical-device ACK.

GET /api/state provides current state and a process-local mutation token. POST
/api/step requires exact expected epoch/tick; stale/duplicate requests fail with 409.
POST /api/reset takes expected epoch and bounded command_id, reusing the existing
reset/receipt contract. Failed validation never advances the simulation. Static routes
are allowlisted. Require the actual loopback Host, same-origin if Origin is present,
mutation token, application/json and body length 1–256 bytes; malformed/unsupported
requests fail closed. Token is not a durable identity or credential; don't log it.
Socket reads time out after 3 seconds. No retry loops or background server mutations.

## Acceptance

- AC-209: deterministic dashboard state/trace projection, visible deterioration,
  correct totals and latest explanation, recent history bounded at 12.
- AC-210: reset and duplicate delivery preserve epoch/counter rules; stale step/reset
  and malformed commands cannot mutate state.
- AC-211: loopback-only server, bundled assets, allowlisted routes and bounded
  same-origin mutation contract; one-command launch and actual-browser verification.

Existing simulator/trace criteria and output remain unchanged. No new dependency,
modeling abstraction, AWS, MQTT, UART or hardware interaction. The full Issue #17
cloud/button demonstration, recording and measured interview rehearsal remain pending.
