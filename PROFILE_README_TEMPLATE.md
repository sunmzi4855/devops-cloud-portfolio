# GitHub Profile README Template

To display the profile below, create a public repository named `sunmzi4855/sunmzi4855` and put the profile text in its root `README.md`.

Copy from the next heading through the LinkedIn link.

---

# Hi, I’m Sunmy

**DevOps and Cloud Engineering | Infrastructure Automation | Service Reliability**

I work with cloud and DevOps technologies to make infrastructure repeatable, automate software delivery, and test how services behave during failures. My portfolio demonstrates Python automation, containerized applications, Kubernetes recovery, Terraform policy checks, and Prometheus alerting.

**Open to fully remote U.S. DevOps and cloud engineering opportunities.**

## Featured engineering labs

These independent portfolio labs have passing GitHub Actions runs. Each guide links to the tested commit while its draft pull request is open.

| Lab and guide | Observed result | Verification |
| --- | --- | --- |
| [Kubernetes pod recovery](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/44c3f43a1f1eb810812c84e51478c208aa24a0bc/labs/kubernetes-recovery/README.md) | Two ready replicas restored in 6.46 seconds after a pod deletion | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43975910651) · [Draft PR #2](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/2) |
| [Terraform AWS network policy](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/ddcd7afdf3f20ff507de4a85b331db1dca5c668b/terraform/aws/lab/README.md) | Safe plan accepted and both unsafe network changes rejected using a mocked AWS provider | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43979854273) · [Draft PR #3](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/3) |
| [Prometheus outage alert](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/2bb344ff6f6a8d959c30f825041513c38b45f46c/monitoring/outage-lab/README.md) | Alert fired in 27.28 seconds and cleared in 5.23 seconds after the stop and start requests | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43981933455) · [Draft PR #4](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/4) |
| [Release health gate](https://github.com/sunmzi4855/devops-cloud-portfolio/blob/bcb0236aa6b1c1d4d870fe3e35fa9e350c5cfd92/reliability/README.md) | Automated tests passed for healthy and failing candidates, response payloads, latency, and CLI validation | [Passed run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/43972322318) · [Draft PR #1](https://github.com/sunmzi4855/devops-cloud-portfolio/pull/1) |

The timing measurements come from individual CI runs in disposable local environments. The Terraform tests use mocked AWS responses.


## Technical focus

| Area | Tools used in these projects |
| --- | --- |
| Infrastructure as code | Terraform, AWS provider |
| Containers and orchestration | Docker, Docker Compose, Kubernetes, Helm, kind |
| Delivery and verification | GitHub Actions, Python unittest |
| Observability | Prometheus, Grafana |
| Automation | Python |

[Explore my DevOps portfolio](https://github.com/sunmzi4855/devops-cloud-portfolio) · [Connect on LinkedIn](https://www.linkedin.com/in/sunmisola-joe-119723255)

---

After creating the profile repository, pin `devops-cloud-portfolio` so visitors can open the code from your profile.
