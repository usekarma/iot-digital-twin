# Threat model

## Worked example boundary

The sample computes on validated local input without persistence or network access. Bounds and type validation protect its input contract. There is no authentication boundary to demonstrate; adding a service changes this model.

## Project review worksheet

List assets and data classification, actors, entry points, authentication/authorization, trust boundaries, secrets, dependencies, abuse cases, mitigations, and residual risks with owners.

For agent workflows: treat fetched content as untrusted; reject instructions to exfiltrate files or credentials, disable checks, or expand authority. Limit tool permissions and review external side effects. Keep sensitive data out of prompts and fixtures. The opt-in audit hook records tool names only and is not an enforcement boundary.

For services: test unauthorized access, injection, input size limits, sensitive log leakage, retry amplification, and privilege boundaries as applicable. Document retention and deletion. Dependency scans and pattern matching complement human review; neither certifies security.

## Offline interview simulator boundary

All events and reset receipts are synthetic, local, and unauthenticated. The CLI accepts
only bounded seed/asset/tick/reset arguments and has no network/device adapter or secret
input. Immutable validated events, configured asset membership, per-asset sequences and
active epochs prevent replay, backward state and cross-generation contamination within
a single run. Memory is bounded to current state plus one reset receipt. The CLI caps
output at 100 ticks for at most 50 assets.

Local epoch counters and seeded randomness are not security identities. A restart loses
state and must begin an isolated rehearsal, never a live session. Do not expose this
consumer as an authenticated service without separate authorization, durable deduplication,
concurrency, resource-limit and recovery designs. The original ignored mbedTLS fixture
artifact limitation remains unchanged; no scanner exclusion is introduced.
