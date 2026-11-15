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

## Limitations

A pattern-based scanner has false positives and misses many real secret formats. Use GitHub secret scanning, a mature secret-detection product, code analysis, image vulnerability scanning and branch protections for production. Never commit real credentials for demonstration purposes. If a real secret is committed, revoke/rotate it immediately; deleting the file does not remove it from Git history.
