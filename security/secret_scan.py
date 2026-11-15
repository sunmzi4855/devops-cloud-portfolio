"""Dependency-free educational secret scanner for tracked source files.

This intentionally uses a narrow set of patterns and cannot replace a dedicated
secret-scanning product. It skips its own source and .git metadata.
"""
import pathlib
import re
import subprocess
import sys

PATTERNS = {
    "AWS access key ID": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub classic PAT": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def scan_file(path):
    try:
        body = pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [label for label, regex in PATTERNS.items() if regex.search(body)]


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    findings = []
    for file in tracked:
        if not file or file == "security/secret_scan.py":
            continue
        for label in scan_file(file):
            findings.append((file, label))
    for path, label in findings:
        print(f"Potential {label} found in {path}")
    if findings:
        print("Security scan failed. Investigate without printing suspected secrets.")
        return 1
    print("No targeted secret patterns found. This is not a comprehensive audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
