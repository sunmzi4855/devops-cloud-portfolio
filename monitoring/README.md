# Local Prometheus + Grafana observability demo

Run from the repository root:

```bash
export GRAFANA_ADMIN_PASSWORD='replace-with-a-strong-local-password'
docker compose -f monitoring/docker-compose.yml up --build -d
```

On Windows PowerShell, set the variable with `$env:GRAFANA_ADMIN_PASSWORD="your-strong-password"`.

Open:
- API health: http://localhost:8080/health
- API metrics: http://localhost:8080/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (user: `admin`, password: your environment variable)

A provisioned **DevOps Health API** dashboard displays uptime and HTTP request rate. Generate sample traffic with `curl http://localhost:8080/health` multiple times.

Shut down with:
```bash
docker compose -f monitoring/docker-compose.yml down
```

Ports are bound to localhost. Do not expose this demonstration deployment publicly. The image tags are demonstrations and should be pinned to digests in production. No cloud account or credentials required.

For an automated failure and recovery exercise, run the [Prometheus API Outage Alert Lab](outage-lab/README.md).
