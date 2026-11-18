# Project 5 — DevSecOps quality gates

This project adds an auditable security check to the CI workflow.

## Controls

- Narrow, dependency-free scan for a few common secret formats in Git-tracked files
- Pipeline fails if a matching pattern appears
- Container runs as non-root and drops Linux capabilities in Kubernetes
- GitHub Actions uses minimal read-only repository permissions

Run from the repository root:

```bash
python security/secret_scan.py
```

## Inspect the tested container image

After the HTTP health check passes, CI exports the same local image by its immutable Docker image ID. Syft inventories its contents in SPDX 2.3 JSON. The check requires a versioned `dpkg` entry from the Debian base image.

Open a successful [CI run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/workflows/ci.yml) and download its `image-sbom-<attempt>` artifact within 30 days. After extracting the zip, run `sha256sum -c SHA256SUMS` to verify the two files. Read `build-info.txt` for the tested image ID, source revision, and package count. This command lists the versioned package entries.

```bash
jq -r '.packages[] | select(.versionInfo) | [.name, .versionInfo] | @tsv' image.spdx.json
```

To reproduce the inventory on Linux, run these commands from the repository root with Docker, Syft, jq, and sha256sum installed.

```bash
docker build --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" -t cloud-devops-demo:local .
report_dir=$(mktemp -d)
bash security/image-sbom.sh cloud-devops-demo:local "$report_dir"
(cd "$report_dir" && sha256sum -c SHA256SUMS)
```

## Limitations

A pattern-based scanner has false positives and misses many real secret formats. Use GitHub secret scanning, a mature secret-detection product, code analysis, image vulnerability scanning and branch protections for production. Never commit real credentials for demonstration purposes. If a real secret is committed, revoke/rotate it immediately; deleting the file does not remove it from Git history.
