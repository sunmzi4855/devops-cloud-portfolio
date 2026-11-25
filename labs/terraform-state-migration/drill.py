"""Rehearse a Terraform address migration against a disposable PostgreSQL server."""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from plan_guard import Rejected, verify


LAB = Path(__file__).resolve().parent
CONFIG = LAB / "config"
RECORDS = {"orders": 240, "audit": 80}
IMAGE = "postgres:17-alpine"


def run(arguments, *, env, cwd=None, allowed=(0,), timeout=180):
    result = subprocess.run(arguments, cwd=cwd, env=env, check=False, timeout=timeout,
                            capture_output=True, text=True)
    if result.returncode not in allowed:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{arguments[0]} {arguments[1]} exited {result.returncode}\n{detail}")
    return result


@contextmanager
def postgres(env):
    container = run(["docker", "run", "--detach", "--env", "POSTGRES_PASSWORD",
                     "--publish", "127.0.0.1::5432", "--tmpfs", "/var/lib/postgresql/data",
                     IMAGE], env=env).stdout.strip()
    try:
        binding = run(["docker", "port", container, "5432/tcp"], env=env).stdout.strip()
        host, port = binding.rsplit(":", 1)
        if host != "127.0.0.1":
            raise RuntimeError(f"unexpected PostgreSQL binding {binding!r}")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ready = run(["docker", "exec", container, "pg_isready", "-h", "127.0.0.1",
                         "-U", "postgres", "-d", "postgres"], env=env, allowed=(0, 1, 2))
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("the lab database did not become ready")
        def sql(database, statement):
            return run(["docker", "exec", "-e", "PGPASSWORD", container, "psql", "-XAtq",
                        "-h", "127.0.0.1", "-v", "ON_ERROR_STOP=1", "-U", "postgres",
                        "-d", database, "-c", statement], env=env).stdout
        yield sql, int(port)
    finally:
        run(["docker", "rm", "--force", "--volumes", container], env=env)


def fingerprint(sql):
    snapshot = {}
    for name in RECORDS:
        metadata = sql(name, "SELECT oid, datconnlimit, (SELECT count(*) FROM entries) "
                             "FROM pg_database WHERE datname = current_database()")
        oid, limit, count = (int(value) for value in metadata.strip().split("|"))
        rows = sql(name, "COPY (SELECT id, cents, memo FROM entries ORDER BY id) TO STDOUT WITH CSV")
        snapshot[name] = {
            "database_oid": oid, "connection_limit": limit, "rows": count,
            "sha256": hashlib.sha256(rows.encode("utf-8")).hexdigest(),
        }
    return snapshot


def must_reject(plan, expected):
    try:
        verify(plan, expected)
    except Rejected as error:
        return str(error)
    raise RuntimeError("the guard accepted an intentionally unsafe plan")


def rehearse(work, env, sql, port):
    expected = json.loads((LAB / "expected-moves.json").read_text())
    shutil.copy(CONFIG / "provider.tf", work)
    shutil.copy(CONFIG / "before/databases.tf", work)
    shutil.copy(CONFIG / ".terraform.lock.hcl", work)
    (work / "terraform.tfvars.json").write_text(json.dumps({"pg_port": port}))

    def tf(*args, allowed=(0,)):
        return run(["terraform", *args], cwd=work, env=env, allowed=allowed)

    def plan(label, *options):
        tf("plan", "-input=false", "-no-color", f"-out={label}.tfplan", *options)
        return json.loads(tf("show", "-json", f"{label}.tfplan").stdout)

    def state_bindings():
        state = json.loads(tf("show", "-json").stdout)
        resources = state["values"]["root_module"]["resources"]
        return {resource["address"]: resource["values"]["id"] for resource in resources}

    tf("init", "-input=false", "-no-color", "-lockfile=readonly")
    tf("plan", "-input=false", "-no-color", "-out=initial.tfplan")
    tf("apply", "-input=false", "-no-color", "initial.tfplan")
    old_bindings = state_bindings()
    if old_bindings.keys() != expected.keys() or set(old_bindings.values()) != set(RECORDS):
        raise RuntimeError("baseline state differs from the migration fixtures")
    for name, count in RECORDS.items():
        sql(name, "CREATE TABLE entries (id integer PRIMARY KEY, cents integer NOT NULL, memo text NOT NULL)")
        sql(name, f"INSERT INTO entries SELECT n, n*17, '{name}-' || n FROM generate_series(1, {count}) AS n")
    before = fingerprint(sql)
    if any(before[name]["rows"] != count for name, count in RECORDS.items()):
        raise RuntimeError("seeded row counts do not match the fixtures")

    shutil.copy(CONFIG / "after/databases.tf", work)
    untracked = plan("missing-moves")
    actions = Counter(action for resource in untracked["resource_changes"] for action in resource["change"]["actions"])
    if actions != {"create": 2, "delete": 2}:
        raise RuntimeError(f"unexpected plan for omitted moves: {actions}")
    first_reason = must_reject(untracked, expected)

    shutil.copy(CONFIG / "after/moves.tf", work)
    mixed = plan("mixed-change", "-var=orders_connection_limit=25")
    updates = [r["address"] for r in mixed["resource_changes"] if r["change"]["actions"] == ["update"]]
    if updates != ['postgresql_database.workload["orders"]']:
        raise RuntimeError(f"the second control should propose updating orders: {updates}")
    second_reason = must_reject(mixed, expected)
    if state_bindings() != old_bindings or fingerprint(sql) != before:
        raise RuntimeError("one of the rejected plans changed the databases or the state addresses")

    safe = plan("approved")
    moved = verify(safe, expected)
    # Apply exactly the saved plan just inspected with terraform show.
    tf("apply", "-input=false", "-no-color", "approved.tfplan")
    final_bindings = state_bindings()
    if final_bindings != {target: old_bindings[source] for source, target in expected.items()}:
        raise RuntimeError(f"unexpected final Terraform database bindings: {final_bindings}")
    after = fingerprint(sql)
    if before != after:
        raise RuntimeError(f"database identity, contents or settings changed: {before} -> {after}")
    final_plan = tf("plan", "-input=false", "-no-color", "-detailed-exitcode", allowed=(0, 2))
    if final_plan.returncode != 0:
        raise RuntimeError("the post-migration plan still proposes changes")
    return {
        "terraform_version": json.loads(tf("version", "-json").stdout)["terraform_version"],
        "postgres_version": sql("postgres", "SHOW server_version").strip(),
        "omitted_moves": {"actions": dict(actions), "decision": "rejected", "reason": first_reason},
        "mixed_change": {"updated_addresses": updates, "decision": "rejected", "reason": second_reason},
        "approved_moves": moved, "before": before, "after": after,
        "state_before": old_bindings, "state_after": final_bindings, "repeat_plan_exit": final_plan.returncode,
    }


def summary(report):
    lines = [
        "## Terraform state migration", "",
        "Omitted moves proposed two creates and two deletes. The guard rejected that plan.",
        "The guard also rejected a mapped move with an unrelated connection-limit update.",
        f"The approved plan moved {len(report['approved_moves'])} addresses. The repeat plan returned 0.", "",
        "| Database | PostgreSQL OID before → after | Rows before → after | SHA-256 of ordered rows |",
        "| --- | --- | --- | --- |",
    ]
    for name, before in report["before"].items():
        after = report["after"][name]
        lines.append(f"| {name} | {before['database_oid']} → {after['database_oid']} | "
                     f"{before['rows']} → {after['rows']} | `{after['sha256']}` |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, help="write comparison results as JSON")
    args = parser.parse_args()
    missing = [tool for tool in ("terraform", "docker") if shutil.which(tool) is None]
    if missing:
        parser.exit(2, "Install the required tools: " + ", ".join(missing) + "\n")
    # Ignore ambient state locations, CLI arguments, workspaces, and PostgreSQL settings.
    env = {key: value for key, value in os.environ.items() if not key.startswith(("TF_", "PG"))}
    password = secrets.token_urlsafe(32)
    env.update(TF_IN_AUTOMATION="1", TF_INPUT="0", PGPASSWORD=password, POSTGRES_PASSWORD=password)
    try:
        with tempfile.TemporaryDirectory(prefix="terraform-state-move-") as temp, postgres(env) as (sql, port):
            report = rehearse(Path(temp), env, sql, port)
        if args.evidence:
            args.evidence.write_text(json.dumps(report, indent=2) + "\n")
        print(summary(report))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Migration drill failed: {error}\n")


if __name__ == "__main__":
    main()
