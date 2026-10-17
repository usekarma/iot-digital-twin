# ATOM Lite button experiment (prepared, not flashed)

This branch extends the E-043 one-shot transport apparatus. See
`specs/atom-lite-button-events.md` for the bounded physical-button contract.
Reuse the existing private provisioning file, dedicated ATOM identity and exact
`devices/atom-lite-001/probe` topic. Do not create a Thing or new policy/certificate.

Compile only with the isolated cached PlatformIO toolchain. Set both
`PLATFORMIO_CORE_DIR` and `PLATFORMIO_BUILD_DIR` to private directories outside Git;
never invoke an upload target during preparation. Frozen hashes and the exact
four-image flash command are retained in the private approval packet.

After explicit flash and experiment approval, use `tools/send_once.py --port PORT
--config PRIVATE/provisioning.json --arm-button`. It checks the distinct
`ATOM_BUTTON_V1 READY` banner, sends paced private configuration with a fresh
128-bit session ID, then explicitly arms the button. No serial command publishes
an event. Observe `BUTTON_ARMED`, release the button, then press it. No automatic
retry or reboot; stop on error/unknown result. Match event IDs and sequences in
AWS; PUBACK alone is not independent console proof.

Credentials stay in RAM and are wiped on terminal paths. USB host/cable and
software-held keys remain trusted; no physical attestation or flash-encryption
assurance. No public secrets, raw serial logs, or operational evidence.

## LED feedback (added before flash review)

The prior eb2a86d image contained no LED control. This revision uses the existing
Arduino core neopixelWrite driver on GPIO27 (one SK6812, GRB; no new dependency).
Blue (0,0,24) spans Wi-Fi/TLS/MQTT connection. Yellow (24,24,0) starts before the
PUBLISH write and remains until exact packet-ID PUBACK or failure. Green (0,24,0)
is set only after validated PUBACK; it persists until another attempt, expiry or
failure. Red (24,0,0) marks connection, clock, publish/unknown and configuration/
command errors. Idle/startup/accepted configuration/normal expiry is off; both
SESSION_COMPLETE and SESSION_EXPIRED turn the LED off. Green proves broker ACK, not human
console visibility. No minimum color dwell time or blocking LED delay is added.
The 120-second window, three-event cap and button debounce are unchanged.

Hardware validation pending: confirm SK6812 GPIO27 and GRB ordering on the actual
unit, dim brightness/color visibility, RMT timing/latch compatibility and operation
alongside Wi-Fi, and whether the yellow interval is visually noticeable. The cached
core driver has no return status; an electrical/driver failure may leave LED output
incorrect without being detected. Serial statuses remain the independent diagnostic.
Reference: https://docs.m5stack.com/en/homeassistant/devices/atom_lite.

### Prepared terminal LED correction

The executed EXP-007 image intentionally left green latched at SESSION_COMPLETE.
Its terminal flag then prevented the expiry path from clearing it. This candidate
uses one terminal policy: normal expiry and third-event completion both turn off;
connection/publish/clock failures and unknown results stay red. PUBACK green may
be brief on the final event because completion immediately clears it; no extra
delay is added. Window/cap, event identity and network behavior are unchanged.
This correction is prepared only, not flashed or hardware validated.
