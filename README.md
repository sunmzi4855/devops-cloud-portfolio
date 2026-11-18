# DevOps & Cloud Engineering Portfolio

![CI](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/ci.yml/badge.svg)
![Security](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/security.yml/badge.svg)

I’m Sunmy, a cloud and DevOps practitioner focused on infrastructure automation, software delivery, and service reliability. This portfolio brings together Python, Docker, Kubernetes, Terraform, Prometheus, and GitHub Actions through reproducible engineering labs.

**Open to fully remote U.S. DevOps and cloud engineering roles.** [LinkedIn](https://www.linkedin.com/in/sunmisola-joe-119723255)

> These are independent demonstration projects, not claims of past employer deployments. Kubernetes, monitoring, and AWS components are provided as runnable examples; their cloud deployment has not been verified.

## Featured engineering labs

These independent portfolio labs have passing GitHub Actions runs. Each guide links to the tested commit while its draft pull request is open.

| Lab and guide | Observed result | Verification |
| --- | --- | --- |
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

Each successful CI build also produces a downloadable [software bill of materials](security/README.md#inspect-the-tested-container-image) for the image that passed the health check. The download includes package versions, the tested image ID, and the Git revision.

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

Future work includes image vulnerability scanning, secure registry publishing, Kubernetes validation in CI, infrastructure plan review, and deployment screenshots.

**Maintainer:** [sunmzi4855](https://github.com/sunmzi4855)
