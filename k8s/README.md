# Kubernetes and Helm deployment

These manifests deploy the sample API to a **local kind cluster**, not a paid cloud cluster.

## Prerequisites
Docker, kind, kubectl, and optionally Helm installed on your computer.

From the repository root:

```bash
docker build -t cloud-devops-demo:local .
kind create cluster --name devops-demo
kind load docker-image cloud-devops-demo:local --name devops-demo
```

Choose **one** deployment method:

### Plain Kubernetes
```bash
kubectl apply -f k8s/
kubectl rollout status deployment/cloud-devops-demo
kubectl port-forward service/cloud-devops-demo 8080:8080
```

### Helm (alternative to plain Kubernetes)
```bash
helm lint ./helm/cloud-devops-demo
helm install cloud-devops-demo ./helm/cloud-devops-demo
kubectl rollout status deployment/cloud-devops-demo
kubectl port-forward service/cloud-devops-demo 8080:8080
```

In another shell, run `curl http://localhost:8080/health` or `curl http://localhost:8080/metrics`.

Cleanup:
```bash
helm uninstall cloud-devops-demo  # only if you used Helm
kind delete cluster --name devops-demo
```

**Note:** Use either `kubectl apply` or Helm in a given cluster to avoid conflicting resource ownership. These examples require local tools and have not been deployed to a public cloud account.
