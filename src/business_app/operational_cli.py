"""Dry-run-first operator entry point; live publication requires explicit approval flag."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404
import time
import uuid
from pathlib import Path

from business_app.mqtt_tls import connect
from business_app.operational_publisher import envelopes, publish_run


def main() -> None:
    """Prepare a synthetic manifest or publish one bounded reviewed run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--execute-approved-publish", action="store_true")
    for name in ("endpoint", "profile", "region", "expected-account", "ca", "certificate", "key"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    if args.execute_approved_publish:
        if not all(
            (
                args.endpoint,
                args.profile,
                args.region,
                args.expected_account,
                args.ca,
                args.certificate,
                args.key,
            )
        ):
            parser.error("live mode requires exact target and local TLS bindings")
        if (
            re.fullmatch(r"[0-9]{12}", args.expected_account) is None
            or re.fullmatch(
                r"[a-z0-9-]+\.iot\." + re.escape(args.region) + r"\.amazonaws\.com", args.endpoint
            )
            is None
        ):
            parser.error("invalid account or region-bound IoT endpoint")
        aws_cli = shutil.which("aws")
        if aws_cli is None:
            parser.error("AWS CLI required for identity verification")
        identity = subprocess.run(  # nosec B603
            [
                aws_cli,
                "sts",
                "get-caller-identity",
                "--profile",
                args.profile,
                "--region",
                args.region,
                "--output",
                "json",
                "--cli-connect-timeout",
                "5",
                "--cli-read-timeout",
                "5",
            ],
            capture_output=True,
            check=True,
            timeout=15,
            text=True,
        )
        if json.loads(identity.stdout)["Account"] != args.expected_account:
            parser.error("account mismatch; no MQTT connection attempted")
        endpoint = subprocess.run(  # nosec B603
            [
                aws_cli,
                "iot",
                "describe-endpoint",
                "--endpoint-type",
                "iot:Data-ATS",
                "--profile",
                args.profile,
                "--region",
                args.region,
                "--output",
                "json",
                "--cli-connect-timeout",
                "5",
                "--cli-read-timeout",
                "5",
            ],
            capture_output=True,
            check=True,
            timeout=15,
            text=True,
        )
        if json.loads(endpoint.stdout)["endpointAddress"] != args.endpoint:
            parser.error("endpoint ownership mismatch; no MQTT connection attempted")
    # Exclusive creation avoids overwriting evidence from a previous run.
    with args.manifest.open("x") as output:
        if not args.execute_approved_publish:
            packets = envelopes(uuid.uuid4().hex, int(time.time()))
            json.dump({"live_attempted": False, "observations": packets}, output)
            print("Dry run only: twenty observations prepared; no network operations.")
            return
        client = connect(args.endpoint, "adage-operational-m1", args.ca, args.certificate, args.key)
        start_wall = time.time()
        start_mono = time.monotonic()
        packets = envelopes(uuid.uuid4().hex, int(start_wall))
        json.dump(
            {
                "live_attempted": True,
                "account": args.expected_account,
                "region": args.region,
                "observations": packets,
            },
            output,
        )
        output.flush()
        index = 0

        def pace(_: float) -> None:
            nonlocal index
            index += 1
            time.sleep(max(0.0, start_mono + index - time.monotonic()))
            if abs((time.time() - start_wall) - (time.monotonic() - start_mono)) > 2:
                raise RuntimeError("wall clock discontinuity; run stopped")
            if time.monotonic() - start_mono > 60:
                raise TimeoutError("publication deadline exceeded")

        try:
            publish_run(packets, client.publish, pace)
        finally:
            client.close()
        print("Twenty MQTT PUBACKs received; SiteWise readback remains NOT_VERIFIED.")


if __name__ == "__main__":
    main()
