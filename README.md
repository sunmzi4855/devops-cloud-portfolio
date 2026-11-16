# DevOps & Cloud Engineering Portfolio

![CI](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/ci.yml/badge.svg)
![Security](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/security.yml/badge.svg)

**Six hands-on portfolio projects** covering application delivery, container orchestration, observability, cloud infrastructure as code, security automation, and release reliability. Built to demonstrate DevOps engineering techniques through source code and reproducible examples.

> These are independent demonstration projects, not claims of past employer deployments. Kubernetes, monitoring, and AWS components are provided as runnable examples; their cloud deployment has not been verified.

## Projects

| Project | Technologies | What it demonstrates |
| --- | --- | --- |
| **01 — CI/CD and containerized API** | Python, Docker, GitHub Actions | Unit/integration tests, container build, non-root runtime, HTTP smoke test |
| **02 — Kubernetes & Helm** | Kubernetes, Helm, kind | 2-replica Deployment, Service, readiness/liveness probes, resource limits, hardened pod |
| **03 — Monitoring & observability** | Prometheus, Grafana, Docker Compose | Live Prometheus metrics endpoint, request counter, preconfigured dashboard |
| **04 — AWS infrastructure as code** | Terraform, AWS VPC, subnets, security groups | Reviewable cloud-network configuration with no automatic apply |
| **05 — DevSecOps quality gate** | Python, GitHub Actions | Source secret-pattern scanning and security-aware CI |

| **06 — Release health gate** | Python, GitHub Actions | HTTP health and latency checks, JSON promotion decision, rollback drill |

## Repository map

- [01 — App and CI workflow](app/main.py) · [Dockerfile](Dockerfile) · [CI Actions](.github/workflows/ci.yml) · [Tests](tests/test_app.py)
- [02 — Kubernetes deployment guide](k8s/README.md) · [Helm chart](helm/cloud-devops-demo/)
- [03 — Monitoring setup](monitoring/README.md) · [Grafana dashboard](monitoring/grafana/dashboards/health-api.json)
- [04 — AWS Terraform network project](terraform/aws/README.md) · [Local Terraform demo](terraform/main.tf)
- [05 — Security automation guide](security/README.md) · [Security Actions](.github/workflows/security.yml)

- [06 — Release health gate and rollback drill](reliability/README.md) · [CLI](reliability/release_gate.py) · [Tests](tests/test_release_gate.py)

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

Add comprehensive image scanning and SBOM generation; secure publishing to a container registry; Kubernetes validation on CI; infrastructure plan review; real deployment screenshots with evidence.

**Maintainer:** [sunmzi4855](https://github.com/sunmzi4855)
