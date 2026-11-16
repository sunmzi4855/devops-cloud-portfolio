# Release Health Gate

This portfolio lab checks whether a candidate can be promoted. A Python CLI probes the candidate's health endpoint and prints a JSON decision that a deployment pipeline can read. The lab uses the portfolio's existing HTTP API and runs locally.

## Run a release drill

From the repository root, start the API in one terminal:

```bash
PORT=8080 python -m app.main
```

In a second terminal, simulate a healthy candidate and then a release configured with the wrong health path:

```bash
python reliability/release_gate.py http://127.0.0.1:8080/health > healthy-report.json
echo "exit: $?"
cat healthy-report.json

python reliability/release_gate.py http://127.0.0.1:8080/missing > failed-report.json
echo "exit: $?"
cat failed-report.json
```

| Scenario | Decision | Exit code |
| --- | --- | --- |
| All 20 probes return HTTP 200 with healthy JSON and the 95th-percentile latency is at most 250 ms | `promote` | 0 |
| Any probe fails or p95 exceeds 250 ms | `hold` | 1 |
| Invalid command-line arguments | CLI error | 2 |

The CLI uses a two-second socket timeout for each probe. It computes p95 using nearest rank across successful probes and reports the probe number and reason for each failure. The existing GitHub Actions test suite covers the HTTP success, bad-route, wrong-payload, invalid-argument, and high-latency cases.

## Respond to a hold

1. Pause the rollout and keep traffic on the stable revision.
2. Read the JSON report. For the simulated 404, check the configured path and verify that it points to the candidate's `/health` endpoint.
3. Fix the route or revert the candidate using the deployment platform. Rerun the gate before promotion and attach both JSON reports to the release record.

This version emits a decision and leaves traffic changes to the deployment system or operator. A future extension can run the gate against a real candidate, retain the report as a build artifact, and wire the result to a rollout controller.
