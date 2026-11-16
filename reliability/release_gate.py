"""Check a release candidate against an HTTP health and latency policy."""
import argparse
import json
import math
import sys
from http.client import HTTPException
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, message, headers, response)


def probe(endpoint, timeout_seconds):
    start = perf_counter()
    try:
        with build_opener(RejectRedirects()).open(endpoint, timeout=timeout_seconds) as response:
            if response.status != 200:
                return None, f"HTTP {response.status}"
            body = response.read(4097)
        elapsed_ms = (perf_counter() - start) * 1000

        if len(body) > 4096:
            return None, "health response exceeds 4096 bytes"
        payload = json.loads(body)
    except HTTPError as error:
        with error:
            return None, f"HTTP {error.code}"
    except (HTTPException, OSError, ValueError) as error:
        return None, type(error).__name__

    if not isinstance(payload, dict) or payload.get("status") != "healthy":
        return None, "health response must contain status=healthy"
    return elapsed_ms, None


def evaluate(endpoint, samples, max_p95_ms, timeout_seconds):
    latencies = []
    failures = []
    for sample in range(1, samples + 1):
        latency, error = probe(endpoint, timeout_seconds)
        if error is None:
            latencies.append(latency)
        else:
            failures.append({"sample": sample, "reason": error})

    latencies.sort()
    p95 = latencies[math.ceil(0.95 * len(latencies)) - 1] if latencies else None
    if failures:
        decision = "hold"
        reason = "one or more probes failed"
    elif p95 > max_p95_ms:
        decision = "hold"
        reason = "p95 latency exceeded the configured limit"
    else:
        decision = "promote"
        reason = "health and latency checks passed"

    return {
        "decision": decision,
        "reason": reason,
        "samples": samples,
        "successful_probes": len(latencies),
        "p95_ms": round(p95, 3) if p95 is not None else None,
        "max_p95_ms": max_p95_ms,
        "probe_failures": failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="Full HTTP(S) health endpoint URL")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--max-p95-ms", type=float, default=250)
    parser.add_argument("--timeout-seconds", type=float, default=2)
    args = parser.parse_args(argv)

    try:
        endpoint = urlsplit(args.endpoint)
        valid_endpoint = (
            endpoint.scheme in {"http", "https"} and endpoint.hostname
            and endpoint.port != 0 and endpoint.username is None
        )
    except ValueError:
        valid_endpoint = False
    if not valid_endpoint:
        parser.error("endpoint must be an HTTP(S) URL without embedded credentials")
    if not 1 <= args.samples <= 100:
        parser.error("--samples must be between 1 and 100")
    if not all(math.isfinite(value) and value > 0 for value in
               (args.max_p95_ms, args.timeout_seconds)):
        parser.error("latency and timeout must be finite positive numbers")

    report = evaluate(args.endpoint, args.samples, args.max_p95_ms, args.timeout_seconds)
    json.dump(report, sys.stdout, indent=2)
    print()
    return 0 if report["decision"] == "promote" else 1


if __name__ == "__main__":
    sys.exit(main())
