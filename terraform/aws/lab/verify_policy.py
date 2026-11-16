"""Exercise the AWS network policy against safe and unsafe plans."""
from pathlib import Path
import shutil
import subprocess
import tempfile

AWS_CONFIG = Path(__file__).resolve().parents[1]
PUBLIC_SSH = """ingress {
    description = "Deliberately unsafe rule for this lab"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }"""


def terraform(directory, *args, timeout=180):
    return subprocess.run(
        ["terraform", f"-chdir={directory}", *args, "-no-color"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def require_result(result, expected_code, label, diagnostic=None):
    print(f"\n--- {label} ---", flush=True)
    print(result.stdout, end="", flush=True)
    if result.returncode != expected_code or (diagnostic and diagnostic not in result.stdout):
        raise SystemExit(f"{label}: unexpected Terraform result (exit {result.returncode})")


def main():
    with tempfile.TemporaryDirectory(prefix="terraform-network-policy-") as temp:
        workspace = Path(temp)
        for source in AWS_CONFIG.glob("*.tf"):
            shutil.copy2(source, workspace)
        shutil.copytree(AWS_CONFIG / "tests", workspace / "tests")

        require_result(terraform(workspace, "init", "-backend=false", "-input=false",
                                 timeout=300), 0, "Provider initialization")
        require_result(terraform(workspace, "test"), 0, "Private network accepted")
        configuration = workspace / "main.tf"
        original = configuration.read_text(encoding="utf-8")

        cases = (
            ("Public IP assignment rejected", "POLICY_PUBLIC_IP",
             "map_public_ip_on_launch = false", "map_public_ip_on_launch = true"),
            ("Public SSH rejected", "POLICY_APP_INGRESS", "ingress = []", PUBLIC_SSH),
        )
        for label, diagnostic, safe_value, unsafe_value in cases:
            if original.count(safe_value) != 1:
                raise SystemExit(f"{label}: expected exactly one matching statement in main.tf")
            configuration.write_text(original.replace(safe_value, unsafe_value, 1), encoding="utf-8")
            require_result(terraform(workspace, "test"), 1, label, diagnostic)

    print("\nVerified the safe plan passes and both unsafe plans are rejected.")


if __name__ == "__main__":
    main()
