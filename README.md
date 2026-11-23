# Sunmy Joseph · DevOps & Cloud Engineering

![CI](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/ci.yml/badge.svg)
![Security](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/security.yml/badge.svg)

I’m Sunmy. I build and test the checks an on-call engineer needs before shipping a release or recovering a service. These seven independent labs cover event-driven Python services, database recovery, Kubernetes, AWS infrastructure as code, monitoring, container security, and CI/CD. Each has source code and a recorded test run.

**Open to fully remote U.S. DevOps and cloud engineering roles.** [LinkedIn](https://www.linkedin.com/in/sunmisola-joe-119723255)

**Latest project · Eight workers, one deployment record.** I sent the same deployment event to eight Python workers at once. One wrote the record, and seven recognized the replay. The lab also exercises a worker crash and shows how to recover a corrected message from a dead-letter queue. [Read the SQS case study](labs/sqs-idempotent-worker/README.md) · [See the test run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44626371210)

## Featured case study · Can we trust this PostgreSQL backup?

A backup job can finish successfully even when the data you need cannot be recovered. I built a Docker-based drill that takes a snapshot of a job queue, writes one more job, and restores the backup into an empty PostgreSQL database.

**250 of 250 records were recovered.** The SHA-256 fingerprint of every ordered row matched the snapshot. The later write stayed out of the restore. To test whether the checks could catch a real problem, the drill also rejected a damaged archive and detected a one-field change that left the row count intact.

[Read the case study and rerun it](labs/postgres-recovery/README.md) · [See the passing GitHub Actions run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44419048693)

## Azure cost investigation

A synthetic Azure export showed a $192 daily increase. Virtual machines in one resource group accounted for $180. The Python investigation checks partition and row counts, includes refunds, and ranks the changes by resource group and meter category. [Explore the cost investigation](labs/azure-cost-anomaly/README.md)

## Featured engineering labs

Open a guide for the implementation or its Actions run for the observed result.

| Lab and guide | Observed result | Verification |
| --- | --- | --- |
| [SQS worker replay and dead-letter recovery](labs/sqs-idempotent-worker/README.md) | Eight concurrent deliveries produced one record and seven replays. Two bad messages reached the dead-letter queue, and the corrected message was recovered. Tested with ElasticMQ and DynamoDB Local. | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44626371210) |
| [PostgreSQL backup and restore](labs/postgres-recovery/README.md) | Recovered 250/250 jobs with matching data fingerprints. The empty-target restore and verification took 54 ms in this lab run. | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44419048693) |
| [Container software bill of materials](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/4541e83d89700d743f331a67bdbdfb9f10dfd906/security/README.md#inspect-the-tested-container-image) | Cataloged 96 SPDX package entries from the image that passed the HTTP smoke test and verified the exported checksums | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44416902736) · [Draft PR #5](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/5) |
| [Kubernetes pod recovery](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/44c3f43a1f1eb810812c84e51478c208aa24a0bc/labs/kubernetes-recovery/README.md) | Two ready replicas restored in 6.46 seconds after a pod deletion | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43975910651) · [Draft PR #2](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/2) |
| [Terraform AWS network policy](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/ddcd7afdf3f20ff507de4a85b331db1dca5c668b/terraform/aws/lab/README.md) | Safe plan accepted and both unsafe network changes rejected using a mocked AWS provider | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43979854273) · [Draft PR #3](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/3) |
| [Prometheus outage alert](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/2bb344ff6f6a8d959c30f825041513c38b45f46c/monitoring/outage-lab/README.md) | Alert fired in 27.28 seconds and cleared in 5.23 seconds after the stop and start requests | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43981933455) · [Draft PR #4](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/4) |
| [Release health gate](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/bcb0236aa6b1c1d4d870fe3e35fa9e350c5cfd92/reliability/README.md) | Automated tests passed for healthy and failing candidates, response payloads, latency, and CLI validation | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43972322318) · [Draft PR #1](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/1) |

The timing measurements come from individual CI runs in disposable local environments. The Terraform tests use mocked AWS responses.

## Foundation projects

| Project | Technologies | What it demonstrates |
| --- | --- | --- |
| **01 — CI/CD and containerized API** | Python, Docker, GitHub Actions | Unit/integration tests, container build, non-root runtime, HTTP smoke test |
| **02 — Kubernetes & Helm** | Kubernetes, Helm, kind | 2-replica Deployment, Service, readiness/liveness probes, resource limits, hardened pod |
| **03 — Monitoring & observability** | Prometheus, Grafana, Docker Compose | Live Prometheus metrics endpoint, request counter, preconfigured dashboard |
| **04 — AWS infrastructure as code** | Terraform, AWS VPC, subnets, security groups | Reviewable cloud-network configuration with no automatic apply |
| **05 — DevSecOps quality gate** | Python, GitHub Actions | Source secret-pattern scanning and security-aware CI |

## Repository map

- [01 — App and CI workflow](app/main.py) · [Dockerfile](Dockerfile) · [CI Actions](.github/workflows/ci.yml) · [Tests](tests/test_app.py)
- [02 — Kubernetes deployment guide](k8s/README.md) · [Helm chart](helm/cloud-devops-demo/)
- [03 — Monitoring setup](monitoring/README.md) · [Grafana dashboard](monitoring/grafana/dashboards/health-api.json)
- [04 — AWS Terraform network project](terraform/aws/README.md) · [Local Terraform demo](terraform/main.tf)
- [05 — Security automation guide](security/README.md) · [Security Actions](.github/workflows/security.yml)

## Project 01: Run the application

```bash
python -m unittest discover -s tests -v
docker build -t cloud-devops-demo:local .
docker run --rm -p 8080:8080 cloud-devops-demo:local
```

Check:
- `http://localhost:8080/health` returns healthy JSON.
- `http://localhost:8080/metrics` returns Prometheus-compatible HTTP request counts.

See [GitHub Actions](../../actions) for automated tests and container smoke tests.

## Project 02: Local Kubernetes

Build the image, create a local cluster with kind, load the image, then install either plain Kubernetes manifests or the Helm chart. Step-by-step commands are in the [Kubernetes guide](k8s/README.md).

## Project 03: Monitoring

```bash
export GRAFANA_ADMIN_PASSWORD='your-strong-local-password'
docker compose -f monitoring/docker-compose.yml up --build -d
```

Access Grafana at `http://localhost:3000` and Prometheus at `http://localhost:9090`. Details: [Monitoring guide](monitoring/README.md). No cloud deployment is required.

## Project 04: Terraform

The [AWS network example](terraform/aws/README.md) is deliberately **not** automatically provisioned, avoiding unexpected cloud charges. The [local Terraform example](terraform/main.tf) generates a JSON manifest without an AWS account.

## Project 05: DevSecOps

```bash
python security/secret_scan.py
```

The [security workflow](.github/workflows/security.yml) checks Git-tracked source for a small set of known secret patterns. This is a training control, not a complete secret-scanning solution.

## Security and scope

- CI permissions are read-only.
- The application container runs as an unprivileged user.
- The Kubernetes example uses readiness/liveness probes and resource limits.
- Grafana and Prometheus are exposed only on localhost in the Compose demo.
- No cloud credentials or payment details are stored in this repository.
- Production hardening would require dependency/image scanning, pinned actions and images, credential management, logging and deployment controls.

## Further enhancements

Future work includes validating backup recovery with a production-sized fixture and exercising registry publishing and deployment to a dedicated cloud test environment.

**Maintainer:** [sunmzi4855](https://github.com/sunmzi4855)
