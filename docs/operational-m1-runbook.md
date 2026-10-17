# Operational M1 — prepare, review, then separately authorize live execution

Local preparation (no AWS/MQTT):

```sh
PYTHONPATH=src python3 -m business_app.operational_cli --manifest /tmp/new-m1-dry-run.json
```

After reviewing implementation PRs, exact resource ownership, target identity,
CloudFormation execution role/permissions, config publication, saved plan/cost/teardown
and separately authorizing deployment: resolve the operational-demo declaration;
apply through Adage under human control. Preserve shared bucket/backend/auth owners.
Provision or select a separately approved local-producer certificate, attach the exact
new publish policy/Thing, and record its certificate ID as expected_principal.
No ATOM credentials, flash or MQTT operation is required. Keep CA/cert/key private and
outside the repository; the program does not issue credentials.

The reviewed live command additionally requires --execute-approved-publish, --endpoint,
--profile, --region, --expected-account, --ca, --certificate and --key. That flag is an
operator acknowledgement AFTER authorization, not approval supplied by a spec.
Run only one producer; manifest is written before publication so failed runs retain
expected observations. QoS failures stop; a failed run is not silently resumed.

After separate read-only authorization, acquire history for the exact deployed alias
from runtime metadata, using AWS CLI get-asset-property-value-history with the explicit
profile/region, start-date=(first timestamp - 1), end-date=last timestamp, max-results=20
and no-paginate. Save the JSON privately. Confirm caller account and resource ownership
independently; a wrong target or denied read is a blocker, never an empty-history pass.
Then compare locally:

```sh
PYTHONPATH=src python3 -m business_app.sitewise_readback --manifest /tmp/live-m1.json --history /tmp/sitewise-history.json
```

Record source/manifest hashes, targets, rule errors, independent values and timed
visibility polling for the live latency goal. The comparator alone proves no latency.
No MQTT/real AWS writes or live readback were executed during implementation tests.
