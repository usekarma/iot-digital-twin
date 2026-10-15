# ATOM Lite physical-button MQTT experiment

Status: PREPARED, NOT FLASHED OR EXECUTED. Human requested the next bounded
Faraday experiment after E-043; this does not change the Core2 product scope.

## Goal and contract

Engineer/operator observes a physical press as a fresh event in the existing AWS
MQTT test client. Baseline E-043 demonstrated one serial-triggered transport with
a fixed nonce, not a physical button or fresh event correlation.

GPIO39, INPUT, active low (M5Stack documentation:
https://docs.m5stack.com/en/homeassistant/devices/atom_lite).
After private CONFIG, explicit ARM_BUTTON opens one 120-second window, capped at
three events. No network before a debounced press. No RUN_ONCE command in this
firmware. A stable 50ms release is required after arm and after each publish;
a stable 50ms press emits one event. Hold/bounce cannot repeat. Presses while
network code blocks are intentionally ignored and not queued. Maximum three
attempts, no automatic retry/reconnect, any failure/unknown result is terminal.
The window deadline prevents new attempts; an admitted attempt may finish later.

The host supplies `secrets.token_hex(16)` as the existing CONFIG nonce field,
now interpreted as session_id; all-zero values are rejected. Each attempted press
consumes sequence 1, 2 or 3 before network I/O. Event ID is session_id + '-' + sequence.
Sequence is session-local, not persistent across boots; event-ID uniqueness is
probabilistic across independently generated 128-bit sessions, not attestation
or a server-side replay defense. The operator must verify a session differs from
previous receipts. Do not reuse a configuration frame on another run.

Payload: device_id=atom-lite-001, event=button_press, session_id (32 lowercase hex),
event_id (session_id-sequence), sequence (JSON integer). Same client and exact
`devices/atom-lite-001/probe` topic; QoS1, no DUP/RETAIN, matching PUBACK, verified
TLS using existing root/certificate/key. QoS1 does not promise exactly-once cloud
delivery; count distinct event IDs and report duplicate deliveries separately.

## Acceptance and failure evidence

B-01: configuration/arm alone and a button held at arm cause no network event.
B-02: released then pressed for >=50ms yields exactly one generated event; bounce
and hold yield none extra. Native tests cover state transitions; hardware proof pending.
B-03: up to three deliberate presses yield unique event IDs and sequences 1,2,3
in both sanitized device output and human-confirmed AWS receipt on the same topic.
B-04: expiry, cap, or error stops processing; no rearm, buffering or retry. Credential
strings wiped on terminal paths; reboot and fresh configuration needed for another run.
B-05: malformed session/sequence rejected, exact wire format tested, no secret output.

Stop on mismatch, unexpected events, missing PUBACK, failed connection, or ambiguous
outcome. Retain negative evidence. Human console confirmation is separately graded;
do not infer console visibility from PUBACK. No AWS mutation is required or authorized.
No durable ingestion, TwinMaker, physical identity or production readiness claims.

## Runbook, risks, and review boundary

Keep 0600 provisioning/key/cert outside Git; never put credentials in argv or logs.
Use standard-speed 115200 and paced 32-byte writes (20ms spacing). RX buffer is
2048 bytes as additional headroom, not a claimed diagnosis of E-043's timeout.
Clock is host UTC set at arm, then advances normally. Firmware and button handling
require real hardware validation after human approval. Existing Core2 identity
must stay untouched. Demo owner is the operator; no background service or SLO.
Up to three small MQTT events per approved window, no added cloud resources.

Review frozen image hashes, partitions, original flash backup, existing ATOM
identity/policy, and device security/chip before any flash. Do not use --force,
erase_flash, eFuse writes, or creation/provisioning APIs. Rollback to the retained
E-043 image set requires separate approval; no automatic rollback. Further execution
requires review of the private flash packet and fresh subscription confirmation.

## LED feedback (added before flash review)

The prior eb2a86d image contained no LED control. This revision uses the existing
Arduino core neopixelWrite driver on GPIO27 (one SK6812, GRB; no new dependency).
Blue (0,0,24) spans Wi-Fi/TLS/MQTT connection. Yellow (24,24,0) starts before the
PUBLISH write and remains until exact packet-ID PUBACK or failure. Green (0,24,0)
is set only after validated PUBACK; it persists until another attempt, expiry or
failure. Red (24,0,0) marks connection, clock, publish/unknown and configuration/
command errors. Idle/startup/accepted configuration/normal expiry is off; final
SESSION_COMPLETE retains acknowledged green. Green proves broker ACK, not human
console visibility. No minimum color dwell time or blocking LED delay is added.
The 120-second window, three-event cap and button debounce are unchanged.

Hardware validation pending: confirm SK6812 GPIO27 and GRB ordering on the actual
unit, dim brightness/color visibility, RMT timing/latch compatibility and operation
alongside Wi-Fi, and whether the yellow interval is visually noticeable. The cached
core driver has no return status; an electrical/driver failure may leave LED output
incorrect without being detected. Serial statuses remain the independent diagnostic.
Reference: https://docs.m5stack.com/en/homeassistant/devices/atom_lite.
