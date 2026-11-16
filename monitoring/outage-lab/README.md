# Prometheus API Outage Alert Lab

This observability lab starts the portfolio's API and Prometheus in Docker Compose, stops the API to simulate an outage, and verifies that the alert fires and clears as the service recovers.

| Phase | Prometheus target | Alert |
| --- | --- | --- |
| Baseline | `up = 1` | Inactive |
| API stopped | `up = 0` | Fires after the 15-second hold period |
| API restarted | `up = 1` | Clears |

Prometheus scrapes every 10 seconds and evaluates rules every 5 seconds. The reported times start at the stop and start requests, so they also reflect container lifecycle and the scrape and evaluation schedules. The rule tracks metrics scrape availability. This exercise covers alert evaluation and recovery, with notification delivery outside its scope.

## Run locally

Install Python 3.8+ and Docker with Compose 2.24.4 or newer. From the repository root:

```bash
python3 monitoring/outage-lab/drill.py
```

The drill uses a unique Compose project and a randomly allocated loopback port for Prometheus. It prints the observed transitions and measured timings, then removes its containers, network, and volumes. Images remain cached locally. In GitHub Actions, the successful run publishes the same evidence in the job summary.

## Respond to the alert

1. Inspect the target's last scrape error in Prometheus and determine whether the endpoint is unreachable, slow, or returning invalid metrics.
2. Check container status and logs, then probe the API health endpoint separately to distinguish a service outage from a metrics-only failure.
3. After restoring the service or correcting the metrics endpoint, confirm the next scrapes succeed and the alert clears.

[Alert rule](../api-alerts.yml) · [GitHub Actions workflow](../../.github/workflows/prometheus-outage-lab.yml)
