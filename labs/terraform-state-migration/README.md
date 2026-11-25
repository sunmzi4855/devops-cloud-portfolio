# Terraform state migration for two PostgreSQL databases

The `orders` and `audit` databases start at numbered Terraform addresses. Naming them by workload makes the configuration easier to change, but a plain rename produces a plan to delete both databases and create two new ones. This lab rehearses the refactor against a live PostgreSQL container with 240 synthetic orders and 80 audit entries.

## Plans under review

| Configuration | Plan | Decision |
| --- | --- | --- |
| Replace the numbered addresses with names | Two creates and two deletes | Reject before apply |
| Supply both address moves and change the orders connection limit | An in-place update is bundled into the migration | Reject before apply |
| Supply only the two reviewed moves | Both objects move in state with zero resource writes | Apply the reviewed plan file |

The Python guard reads the saved plan's JSON and compares each old and new address with an independently specified map. Every resource action must be a no-op. The guard also checks for imports, deferred changes, drift and output changes. It runs before the migration is applied. [Review the guard](plan_guard.py) · [Expected moves](expected-moves.json) · [Terraform moved blocks](config/after/moves.tf)

## How to verify the result

The Terraform provider identifies these databases by name. A new database can reuse an old name, so the drill also asks PostgreSQL for the catalog object ID (OID) of each database. It records each OID, connection limit, row count and SHA-256 digest of the ordered rows before the move and again afterward. Success also requires exactly the two new addresses in state and exit code `0` from a fresh `terraform plan -detailed-exitcode`.

## Run the lab

Use Terraform 1.12.2, Python 3.10 or newer, and a local Docker engine. Start in the repository root.

```sh
cd labs/terraform-state-migration
python3 -m unittest -v
python3 drill.py --evidence state-migration.json
```

The drill creates a temporary working directory for Terraform's local state and saved plans. It starts PostgreSQL 17 on a random loopback port and uses a fresh password for that run. It removes the container and working directory afterward. The evidence file contains the observed database identifiers, row counts, hashes, addresses and plan decisions.

The examples use a disposable local environment. A production migration would also need the target backend's state lock, a recoverable backup and checks suited to the workload. [Terraform's refactoring guide](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)

[Run script](drill.py) · [Before configuration](config/before/databases.tf) · [After configuration](config/after/databases.tf) · [GitHub Actions workflow](../../.github/workflows/terraform-state-migration.yml)
