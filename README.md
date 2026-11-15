# Cloud Infrastructure & CI/CD Automation

A hands-on DevOps portfolio project demonstrating an automated quality gate for a containerized Python HTTP service. Includes GitHub Actions CI, Docker image construction, HTTP endpoint tests, and a no-cost Terraform infrastructure-as-code example.

> **Status:** Demonstration project. This repository does not claim production deployment, paid cloud provisioning, or work performed for an employer.

## Architecture

```text
Git push / pull request
         |
   GitHub Actions
         |
   Python API tests
         |
   Docker image build
         |
   Container smoke test
         |
  GET /health -> 200 OK
```

## Technology stack

- **Python 3.12:** Standard-library HTTP service
- **GitHub Actions:** Continuous integration and automated checks
- **Docker:** Non-root container and health check
- **Terraform:** Local-only infrastructure-as-code demonstration (no cloud charges)
- **Testing:** Python unittest and HTTP smoke tests

## Quick start

Run locally from the repository root:

```bash
python -m app.main
```

Visit `http://localhost:8080/health` and expect `{"status": "healthy", "service": "cloud-devops-demo"}`.

Run tests:

```bash
python -m unittest discover -s tests -v
```

Build and run Docker:

```bash
docker build -t cloud-devops-demo .
docker run --rm -p 8080:8080 cloud-devops-demo
```

## Terraform demo

The Terraform configuration creates a local JSON deployment manifest, not AWS, Azure, or GCP infrastructure.

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform apply
terraform destroy
```

The generated `deployment-info.json` and Terraform state files are ignored by Git.

## CI/CD workflow

See [CI workflow](.github/workflows/ci.yml). On pushes, pull requests, or manual dispatch, GitHub Actions runs tests, builds the Docker image and checks the live container's health endpoint.

[View GitHub Actions runs](../../actions)

## Security practices

Container runs as a non-root user; the CI workflow has read-only repository permissions; no credentials are required or stored. For production use, add image scanning, pinned dependencies, authentication, TLS, logging and deployment controls.

## Next improvements

1. Add container vulnerability scanning.
2. Add a Kubernetes deployment and Helm chart.
3. Add observability with Prometheus and Grafana.
4. Provide optional, cost-controlled AWS or Azure infrastructure with Terraform.

## Interview discussion

Explain how automated quality checks catch regressions, how Docker standardizes deployments, how health checks work, and the distinction between Terraform `plan` and `apply`.
