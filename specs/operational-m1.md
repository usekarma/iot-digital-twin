# Operational telemetry M1 implementation

AC-216 is local-contract evidence only. Reuse unchanged GridSimulator seeded rules;
select asset-000 from each of exactly 20 ticks. Asset-000 begins CRITICAL, so this
first ingestion proof intentionally has constant severity; five-asset progression is M2.
Wire metadata wraps the unchanged observation, with run UUID, synthetic label and unique
real wall-clock timestamps. Simulated 60-second time is not a SiteWise timestamp.

M1 uses standard-library MQTT 3.1.1 over X.509 mutual TLS/8883: clean session,
keepalive 60, sequential QoS1 packet IDs 1–20, matching PUBACK required. Socket timeout
is five seconds, response/payload bound 4096 bytes, no subscription/reconnect/retry.
Pacing uses monotonic time; clock discontinuity or elapsed deadline stops the run.
Failure may leave a partial cloud history: never claim atomic or exactly-once delivery.
TLS uses CA/hostname verification and local client cert/key; no credentials in Git.

Default CLI writes a new manifest and makes no network calls. Live mode requires
explicit execute-approved-publish and exact account/profile/region/ATS endpoint plus
local TLS paths. STS and DescribeEndpoint must agree before any MQTT connection.
An evidence file is created exclusively; no overwritten prior evidence. No automated
approval or cloud/device credential creation. PUBACK means broker receipt only.

One exact MQTT topic maps one fixed SiteWise INTEGER severity property, GOOD quality,
real seconds/nanos. The native rule checks reviewed certificate principal, synthetic
schema, asset and bounded tick/sequence/severity. It rejects malformed rule inputs;
error logging captures action failures, while filtered inputs do not invoke the action.
The trusted producer locally validates exact envelopes. This is not a hostile-input
JSON-schema ingestion service or durable sequence/epoch consumer. Reset is out of M1.

Independent readback compares exactly 20 good TQVs against a live-attempt manifest;
missing/conflicting/duplicate/paginated responses fail. Saved API output is operator
supplied, not a cryptographic attestation. No latency proof is inferred: the proposed
19/20 within ten seconds and 20/20 within sixty still require timed live observations.
Only one run/producer may use the asset at a time; timestamp collisions can overwrite
SiteWise values. Replays must use fresh run times and IDs. Preserve raw event keys for
future analytics; M1 SiteWise stores severity history, not complete trace/event metadata.
