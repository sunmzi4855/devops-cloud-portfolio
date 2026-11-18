"""Exercise Prometheus alerting against the portfolio's Docker Compose stack."""
from contextlib import suppress
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
ALERT = "DemoAPIMetricsUnavailable"
JOB = "cloud-devops-demo"


def compose_runner(project):
    command = [
        "docker", "compose", "--project-name", project,
        "-f", "monitoring/docker-compose.yml",
        "-f", "monitoring/outage-lab/compose.override.yml",
    ]
    env = dict(os.environ)
    # Compose resolves this value even though the lab starts only the API and Prometheus.
    env.setdefault("GRAFANA_ADMIN_PASSWORD", "unused-by-outage-lab")

    def compose(*args, timeout=45, capture=False):
        return subprocess.run(
            [*command, *args], cwd=ROOT, env=env, text=True, check=True,
            timeout=timeout, stdout=subprocess.PIPE if capture else None,
        ).stdout

    return compose


def prometheus_data(base_url, path):
    with urlopen(f"{base_url}/api/v1/{path}", timeout=3) as response:
        result = json.load(response)
    if result["status"] != "success":
        raise RuntimeError(f"Prometheus did not return success for {path}")
    return result["data"]


def observe(base_url):
    alerts = prometheus_data(base_url, "alerts")["alerts"]
    query = urlencode({"query": f'up{{job="{JOB}"}}'})
    samples = prometheus_data(base_url, f"query?{query}")["result"]
    up = float(samples[0]["value"][1]) if len(samples) == 1 else None
    states = {
        alert["state"]
        for alert in alerts
        if alert["labels"].get("alertname") == ALERT
        and alert["labels"].get("job") == JOB
    }
    return up, states


def wait_for(base_url, stage, expected_up, expected_states, started):
    deadline = time.monotonic() + 75
    last_observation = "waiting for Prometheus"
    while time.monotonic() < deadline:
        try:
            up, states = observe(base_url)
        except (URLError, TimeoutError, HTTPException) as error:
            last_observation = str(error)
        else:
            last_observation = f"up={up}, alert_states={sorted(states)}"
            if up == expected_up and states == expected_states:
                elapsed = round(time.monotonic() - started, 2)
                print(f"{stage}: {last_observation} after {elapsed}s", flush=True)
                return elapsed
        time.sleep(1)
    raise RuntimeError(f"{stage} timed out. Last observation: {last_observation}")


def drill(compose):
    compose("up", "--detach", "--build", "api", "prometheus", timeout=300)
    endpoint = compose("port", "prometheus", "9090", capture=True).strip()
    if not re.fullmatch(r"127\.0\.0\.1:[1-9][0-9]*", endpoint):
        raise RuntimeError(f"Expected a dynamically allocated loopback endpoint, got {endpoint!r}")
    url = f"http://{endpoint}"
    wait_for(url, "Healthy baseline", 1, set(), time.monotonic())

    started = time.monotonic()
    compose("stop", "--timeout", "1", "api")
    detection = wait_for(url, "Alert firing", 0, {"firing"}, started)

    started = time.monotonic()
    compose("start", "api")
    recovery = wait_for(url, "Alert cleared", 1, set(), started)
    return {
        "alert": ALERT,
        "sequence": ["healthy", "firing", "cleared"],
        "seconds_from_stop_request_to_firing": detection,
        "seconds_from_start_request_to_clear": recovery,
    }


def main():
    compose = compose_runner(f"outage-lab-{uuid4().hex[:8]}")
    try:
        report = drill(compose)
    except (Exception, KeyboardInterrupt):
        with suppress(subprocess.SubprocessError):
            compose("logs", "--tail", "60", "api", "prometheus")
        with suppress(subprocess.SubprocessError):
            compose("down", "--volumes", "--remove-orphans")
        raise
    else:
        compose("down", "--volumes", "--remove-orphans")

    evidence = json.dumps(report, indent=2)
    print(evidence)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"## Prometheus outage alert drill\n\n~~~json\n{evidence}\n~~~\n")


if __name__ == "__main__":
    main()
