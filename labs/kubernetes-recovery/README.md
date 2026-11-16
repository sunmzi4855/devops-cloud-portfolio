# Kubernetes Pod Recovery Lab

This DevOps lab injects a pod failure into a two-replica Kubernetes Deployment. A Python script starts a disposable kind cluster, deploys the portfolio's containerized API, and verifies recovery.

1. Wait for two ready API pods and verify the API through Kubernetes Service DNS.
2. Delete one pod and start measuring recovery.
3. Confirm the surviving pod stays ready and the Deployment has a new ready pod with a different UID.
4. Verify the Service again and record the observed recovery time and pod names.
5. Delete the lab cluster on exit.

The Service health checks run before and after deletion. The measured recovery time covers the deletion request through observation of two ready pods. This lab simulates a single pod deletion on a local cluster. Node failures, traffic continuity, and production recovery objectives require separate drills.

## Run locally

Install Python 3.8+, Docker, kind, and kubectl. From the repository root:

```bash
python3 labs/kubernetes-recovery/drill.py
```

The command builds the API image and uses a temporary kubeconfig for the lab cluster. It prints JSON evidence on success and an error on failure. The local Docker image remains available after cleanup. GitHub Actions also runs the drill and includes the evidence in its job summary.

## Investigate a failed drill

Start with the pod listing and Kubernetes events printed before cluster cleanup. For an image error, confirm that the local tag matches the Deployment and was loaded into the kind cluster. For readiness failures, inspect the `/health` probe and container startup. If the pods are ready but the Service check fails, inspect its port, selector, and EndpointSlices.

## Portfolio discussion

Explain how the Deployment controller restores the desired replica count, why a new UID confirms replacement, and what additional monitoring you would add to measure customer-visible availability during the incident.
