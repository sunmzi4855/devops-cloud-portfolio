#!/usr/bin/env python3
"""Verify that a local Kubernetes Deployment replaces a deleted pod."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
APP = "cloud-devops-demo"
IMAGE = f"{APP}:local"
RECOVERY_TIMEOUT_SECONDS = 90
HEALTH_CHECK = """import json
from urllib.request import urlopen

with urlopen("http://cloud-devops-demo:8080/health", timeout=5) as response:
    if response.status != 200 or json.load(response).get("status") != "healthy":
        raise SystemExit("Service did not return healthy JSON")
"""


def run(*command, timeout=30, capture=False):
    result = subprocess.run(
        command, cwd=ROOT, check=True, timeout=timeout, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout


def ready_pods(kubectl):
    pods = json.loads(kubectl("get", "pods", "--output=json", capture=True))
    return {
        pod["metadata"]["uid"]: pod["metadata"]["name"]
        for pod in pods["items"]
        if not pod["metadata"].get("deletionTimestamp")
        and any(
            condition["type"] == "Ready" and condition["status"] == "True"
            for condition in pod.get("status", {}).get("conditions", [])
        )
    }


def verify_recovery(kubectl):
    kubectl("apply", "-f", "k8s/")
    kubectl("rollout", "status", f"deployment/{APP}", "--timeout=120s", timeout=130)
    before = ready_pods(kubectl)
    if len(before) != 2:
        raise RuntimeError(f"Expected two ready API pods, found {len(before)}")

    victim, survivor = before.values()
    kubectl("exec", survivor, "--", "python", "-c", HEALTH_CHECK)
    print(f"Deleting {victim} after a successful baseline service check.", flush=True)

    started = time.monotonic()
    kubectl("delete", "pod", victim, "--wait=false")
    while time.monotonic() - started < RECOVERY_TIMEOUT_SECONDS:
        after = ready_pods(kubectl)
        replacements = after.keys() - before.keys()
        if (
            len(after) == 2
            and victim not in after.values()
            and survivor in after.values()
            and len(replacements) == 1
        ):
            elapsed = time.monotonic() - started
            if elapsed > RECOVERY_TIMEOUT_SECONDS:
                break
            replacement = after[replacements.pop()]
            kubectl("exec", survivor, "--", "python", "-c", HEALTH_CHECK)
            return {"deleted_pod": victim, "surviving_pod": survivor,
                    "replacement_pod": replacement, "ready_pods": len(after),
                    "recovery_seconds": round(elapsed, 2),
                    "service_check_before_and_after": "passed"}
        time.sleep(1)
    raise RuntimeError(f"Deployment did not recover within {RECOVERY_TIMEOUT_SECONDS}s")


def main():
    missing = [name for name in ("docker", "kind", "kubectl") if not shutil.which(name)]
    if missing:
        raise SystemExit(f"Install required commands: {', '.join(missing)}")

    cluster = f"recovery-{uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="pod-recovery-") as directory:
        config = str(Path(directory) / "kubeconfig")

        def kubectl(*args, **kwargs):
            return run("kubectl", "--kubeconfig", config, *args, **kwargs)

        run("docker", "build", "--tag", IMAGE, ".", timeout=300)
        run("kind", "create", "cluster", "--name", cluster, "--kubeconfig", config,
            "--wait", "90s", timeout=300)
        try:
            run("kind", "load", "docker-image", IMAGE, "--name", cluster, timeout=180)
            report = verify_recovery(kubectl)
        except (RuntimeError, subprocess.SubprocessError):
            kubectl("get", "pods", "--output=wide")
            kubectl("get", "events", "--sort-by=.metadata.creationTimestamp")
            raise
        finally:
            run("kind", "delete", "cluster", "--name", cluster, "--kubeconfig", config,
                timeout=90)

    evidence = json.dumps(report, indent=2)
    print(evidence)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"## Kubernetes pod recovery drill\n\n~~~json\n{evidence}\n~~~\n")


if __name__ == "__main__":
    main()
